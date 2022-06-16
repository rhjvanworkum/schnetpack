import numpy as np
import matplotlib.pyplot as plt

class PySCFResult:
  def __init__(self, ml, index, t_tot, imacro, guess, converged, S, fci_vec=None, P_guess=None, P_conv=None, occ_guess=None, occ_conv=None) -> None:
    self.ml = ml
    self.index = index
    self.t_tot = t_tot
    self.imacro = imacro
    self.guess = guess
    self.converged = converged
    self.S = S
    self.fci_vec = fci_vec
    self.P_guess = P_guess
    self.P_conv = P_conv
    self.occ_guess = occ_guess
    self.occ_conv = occ_conv

def extract_results(split_file, base_dir, CASSCF=False):
  indices = np.load(split_file)['val_idx']

  if CASSCF:
    converged_property = 'mo_coeffs'
  else:
    converged_property = 'dm_final'

  results = []
  for index in indices:
    # add HF Results
    result = np.load(base_dir + 'geometry_' + str(index) + '.npz')
    results.append(PySCFResult(ml=False,
                               index=index,
                               t_tot=result['t_tot'],
                               imacro=result['imacro'],
                               guess=result['guess'],
                               converged=result[converged_property],
                               S=result['S'],))
                              #  fci_vec=result['fcivec']))

    # add HF_ML Results
    result = np.load(base_dir + 'geometry_' + str(index) + '_ML.npz')
    results.append(PySCFResult(ml=True,
                               index=index,
                               t_tot=result['t_tot'],
                               imacro=result['imacro'],
                               guess=result['guess'],
                               converged=result[converged_property],
                               S=result['S'],))
                              #  fci_vec=result['fcivec']))

  hf_results = list(filter(lambda x: not x.ml, results))
  ml_results = list(filter(lambda x: x.ml, results))
  return hf_results, ml_results