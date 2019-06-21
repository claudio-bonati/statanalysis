#!/usr/bin/env python3

import numpy as np
import scipy.misc as spm

__all__ = ["multihisto_for_primary", "multihisto_for_secondary"]


def newlzeta(energyfunc, lzeta, stuff, speedup):
  """
  The values of the partition functions to be computed are fixed points of this function
  
  energyfunc is the function to compute the 'energy'

  stuff is a list whose elements are of the form
  stuff[i]=[param_i, vecdata_i, blockdata_i]
  with vecdata=[column0, column1, .... ]

  speedup >=1 is an integer
  """
 
  betas=np.array([element[0] for element in stuff])
  stat=np.array([len(np.transpose(element[1])) for element in stuff])

  lzetanew=[]

  for betavalue in betas:
    aux=[]
    for element in stuff:
      end=element[2]*int(len(np.transpose(element[1]))/element[2])
  
      energy=energyfunc(element[1][:end])

      tmp = np.array([ (-1)*spm.logsumexp(  np.sum(np.stack((np.log(stat), -lzeta, (betavalue-betas)*value), axis=1), axis=1) ) for value in energy[0:end:speedup] ])

      aux.append(spm.logsumexp(tmp))

    lzetanew.append(spm.logsumexp(np.array(aux)))

  return np.array(lzetanew)


def computelzeta(energyfunc, stuff, *args):
  """
  Compute the log of the partition functions in a self-consistent way

  energyfunc is the function to compute the 'energy'

  stuff is a list whose elements are of the form
  stuff[i]=[param_i, vecdata_i, blockdata_i]
  with vecdata=[column0, column1, .... ]
  """

  speedup=100

  if len(args)==0:
    lzetaold=np.ones(len(stuff))
  else:
    lzetaold=np.copy(args[0])
    speedup=1

  lzetanew=newlzeta(energyfunc, lzetaold, stuff, speedup)
  check=np.linalg.norm(lzetanew-lzetaold)
  lzetanew-=(lzetanew[0]-1)
  check=np.linalg.norm(lzetanew-lzetaold)

  while speedup>1:
    lzetaold=np.copy(lzetanew)
    lzetanew=newlzeta(energyfunc, lzetaold, stuff, speedup)
    lzetanew-=(lzetanew[0]-1)
    check=np.linalg.norm(lzetanew-lzetaold)

    while check>1e-2:
      lzetaold=np.copy(lzetanew)
      lzetanew=newlzeta(energyfunc, lzetaold, stuff, speedup)
      lzetanew-=(lzetanew[0]-1)
      check=np.linalg.norm(lzetanew-lzetaold)

      print("computing lzeta: {:12.8f} ({:8d})".format(check, speedup), end='\r')

    speedup=int(speedup/2)
    if speedup<1:
      speedup=1

  while check>1e-4:
    lzetaold=np.copy(lzetanew)
    lzetanew=newlzeta(energyfunc, lzetaold, stuff, speedup)
    lzetanew-=(lzetanew[0]-1)
    check=np.linalg.norm(lzetanew-lzetaold)
    print("computing lzeta: {:12.8f} ({:8d})".format(check, speedup), end='\r' )

  return lzetanew


def jack_for_primary(func, param, energyfunc, lzeta, stuff):
  """
  func is the function of the primaries to be comuted,

  param is the value of the control parameter ('beta')

  energyfunc is the function to compute the 'energy'

  lzeta is the log of the partition functions 

  stuff is a list whose elements are of the form
  stuff[i]=[param_i, vecdata_i, blockdata_i]
  with vecdata=[column0, column1, .... ]
  """

  betas=np.array([element[0] for element in stuff])
  stat=np.array([len(np.transpose(element[1])) for element in stuff])
  numblocks=np.sum(np.array([int(len(np.transpose(element[1]))/element[2]) for element in stuff]) )

  auxZ=[]
  auxO=[]
  for element in stuff:
    end=element[2]*int(len(np.transpose(element[1]))/element[2])
  
    energy=energyfunc(element[1])
    obs=func(element[1])

    tmpZ = np.array([ (-1)*spm.logsumexp(  np.sum(np.stack((np.log(stat), -lzeta, (param-betas)*value), axis=1), axis=1) ) for value in energy[:end] ])
    tmpO = tmpZ+np.log(obs[:end])
 
    auxZ = np.concatenate(( auxZ, spm.logsumexp( np.reshape(tmpZ,(-1, element[2])), axis=1) ))
    auxO = np.concatenate(( auxO, spm.logsumexp( np.reshape(tmpO,(-1, element[2])), axis=1) ))
 
  sumZ=spm.logsumexp(auxZ)
  sumO=spm.logsumexp(auxO)

  sumZb=np.tile(sumZ, len(auxZ)) 
  sumOb=np.tile(sumO, len(auxO)) 

  jack=np.exp( spm.logsumexp( np.stack((sumOb, auxO), axis=1), b=[1,-1], axis=1) - spm.logsumexp( np.stack((sumZb, auxZ), axis=1), b=[1,-1], axis=1) )

  return np.exp(sumO-sumZ), np.std(jack)*np.sqrt(numblocks-1)


def multihisto_for_primary(param_min, param_max, num_steps, energyfunc, func, stuff):
  """
  Compute the primary function func using multihistogram reweighting techniques
  for num_steps values of the control parameter, going from param_min to
  param_max.

  energyfunc is the function to compute the 'energy'

  stuff is a list, whose elements of the form
  stuff[i]=[param_i, vecdata_i, blockdata_i]
  with vecdata=[column0, column1, .... ]
  """

  for arg in stuff:
    if not isinstance(arg[2], int):
      print("ERROR: blocksize has to be an integer!")
      sys.exit(1)
  
    if arg[2]<1:
      print("ERROR: blocksize has to be positive!")
      sys.exit(1)

  lzeta=computelzeta(energyfunc, stuff);

  print("log(zeta) = ", lzeta)
  print("")

  for i in range(num_steps+1):
    param=param_min+i*(param_max-param_min)/num_steps
    ris, err = jack_for_primary(func, param, energyfunc, lzeta, stuff) 
    print("{:.8f} {:.12g} {:.12g}".format(param, ris, err) )


def jack_for_secondary(func2, param, energyfunc, lzeta, vecfunc, stuff):
  """
  func2 is the function to be computed, 

  param is the value of the control parameter ('beta')

  energyfunc is the function to compute the 'energy'

  lzeta is the log of the partition functions 

  vecfunc=[func1a, func1b, func1c..... ] 
  where func1a, func1b and so on are the functions of the
  primaries that are needed for func2.

  stuff is a list whose elements are of the form
  stuff[i]=[param_i, vecdata_i, blockdata_i]
  with vecdata=[column0, column1, .... ]
  """

  # list of primary jackknife samples
  jack_list=[]

  # list of average values of the primary observables
  mean_list=[]

  betas=np.array([element[0] for element in stuff])
  stat=np.array([len(np.transpose(element[1])) for element in stuff])
  numblocks=np.sum(np.array([int(len(np.transpose(element[1]))/element[2]) for element in stuff]) )

  for func1 in vecfunc:
    auxZ=[]
    auxO=[]
    for element in stuff:
      end=element[2]*int(len(np.transpose(element[1]))/element[2])
    
      energy=energyfunc(element[1])
      obs=func1(element[1])
  
      tmpZ = np.array([ (-1)*spm.logsumexp(  np.sum(np.stack((np.log(stat), -lzeta, (param-betas)*value), axis=1), axis=1) ) for value in energy[:end] ])
      tmpO = tmpZ+np.log(obs[:end])
   
      auxZ = np.concatenate(( auxZ, spm.logsumexp( np.reshape(tmpZ,(-1, element[2])), axis=1) ))
      auxO = np.concatenate(( auxO, spm.logsumexp( np.reshape(tmpO,(-1, element[2])), axis=1) ))
   
    sumZ=spm.logsumexp(auxZ)
    sumO=spm.logsumexp(auxO)
  
    sumZb=np.tile(sumZ, len(auxZ)) 
    sumOb=np.tile(sumO, len(auxO)) 
  
    jack_list.append( np.exp( spm.logsumexp( np.stack((sumOb, auxO), axis=1), b=[1,-1], axis=1) - spm.logsumexp( np.stack((sumZb, auxZ), axis=1), b=[1,-1], axis=1) ) )
    mean_list.append( np.exp(sumO-sumZ) )
  
  secondary_jack=func2(jack_list) #jackknife sample
  
  ris_no_bias=numblocks*func2(mean_list) -(numblocks-1)*np.mean(secondary_jack)
  err=np.std(secondary_jack)*np.sqrt(numblocks-1)

  return ris_no_bias, err


def multihisto_for_secondary(param_min, param_max, num_steps, func2, vecfunc, stuff):
  """
  Compute the secondary function func2 using multihistogram reweighting
  techniques for num_steps values of the control parameter, going from param_min
  to param_max.

  vecfunc=[func1a, func1b, func1c..... ]
  where func1a, func1b and so on are the functions of the
  primaries that are needed for func2.

  stuff is a list whose elements are of the form
  stuff[i]=[param_i, vecdata_i, blockdata_i]
  with vecdata=[column0, column1, .... ]
  """

  for arg in stuff:
    if not isinstance(arg[2], int):
      print("ERROR: blocksize has to be an integer!")
      sys.exit(1)
  
    if arg[2]<1:
      print("ERROR: blocksize has to be positive!")
      sys.exit(1)

  lzeta=computelzeta(energyfunc, stuff);

  print("log(zeta) = ", lzeta)
  print("")

  for i in range(num_steps+1):
    param=param_min+i*(param_max-param_min)/num_steps
    ris, err = jack_for_secondary(func2, param, lzeta, stuff, vecfunc) 
    print("{:.8f} {:.12g} {:.12g}".format(param, ris, err) )



#***************************
# unit testing



if __name__=="__main__":
  
  print("**********************")
  print("UNIT TESTING")
  print()

  #indata=np.loadtxt("dati_2.26.dat", skiprows=500, dtype=np.float)
  #data226=np.transpose(indata)     #column ordered

  #indata=np.loadtxt("dati_2.27.dat", skiprows=500, dtype=np.float)
  #data227=np.transpose(indata)     #column ordered

  #indata=np.loadtxt("dati_2.28.dat", skiprows=500, dtype=np.float)
  #data228=np.transpose(indata)     #column ordered

  #def energy(vec):
  #  return 6*4*8**3*(1-(vec[0]+vec[1])/2)

  #def plaq(vec):
  #  return (vec[0]+vec[1])/2.0

  #def squareplaq(vec):
  #  return (vec[0]+vec[1])*(vec[0]+vec[1])/4.0

  #def susc(v):
  #  return v[0]-v[1]*v[1]

  #stuff=[[2.26, data226, 20], [2.27, data227, 20], [2.28, data228, 100]]

  #multihisto_for_secondary(2.26, 2.28, 20, susc, [squareplaq, plaq], stuff)

  print("**********************")

