import torch

"""
Util Functions
"""
# MO overlap measure
def mo_overlap(C_1, C_2, overlap_matrix):
  return 0.5 * torch.einsum('i,j,ij', C_1, C_2, overlap_matrix)

# overlap of a set of MO's
def overlap(mo_coeffs_1, mo_coeffs_2, overlap_matrix):
    overlap_m = torch.zeros((36, 36))
    for i in range(36):
        for j in range(36):
            overlap_m[i, j] = mo_overlap(mo_coeffs_1[:, i], mo_coeffs_2[:, j], overlap_matrix)
    return torch.abs(torch.linalg.det(overlap_m)) * 1e14

# calculate Density Matrix
def density_matrix(orbitals, occ):
  return torch.einsum('i,ij,ik->jk', occ, orbitals, orbitals)

# calculate Wavefunction projection measure
def projection(pred, target, S, guess_occ, conv_occ):
    P_guess = density_matrix(pred, guess_occ)
    P_conv = density_matrix(target, conv_occ)
    return torch.trace(torch.matmul(P_guess, torch.matmul(S, torch.matmul(P_conv, S))))

# total mo energy of a given hamiltonian
def total_mo_energy(pred, target, overlap):
    e_s, U = torch.linalg.eig(overlap)
    diag_s = torch.diag(e_s ** -0.5)
    X = torch.matmul(U, torch.matmul(diag_s, U.T))

    F_pred_prime = torch.matmul(X.T, torch.matmul(pred.type(torch.complex64), X))
    mo_e_pred, _ = torch.linalg.eig(F_pred_prime)
    mo_e_pred = mo_e_pred.type(torch.float32)

    F_target_prime = torch.matmul(X.T, torch.matmul(target.type(torch.complex64), X))
    mo_e_target, _ = torch.linalg.eig(F_target_prime)
    mo_e_target = mo_e_target.type(torch.float32)

    return torch.sum(torch.abs(mo_e_target - mo_e_pred))


"""
Loss Functions for learned MO coefficients - matrix C
"""
# RMSE loss fn
def mean_squared_error(pred, targets, basis_set_size):
    pred = pred.reshape(-1, basis_set_size, basis_set_size)
    targets = targets.reshape(-1, basis_set_size, basis_set_size)
    batch_size = pred.shape[0]
    loss = 0
    for i in range(batch_size):
        loss += torch.sum(torch.square(targets[i].flatten() - pred[i].flatten())) / basis_set_size**2
    return loss / batch_size

# Weighted MSE given a set of weights
def weighted_mse(pred, targets, weights):
    targets = targets.reshape(-1, 36**2)
    pred = pred.reshape(-1, 36**2)

    loss = 0
    for i in range(pred.shape[0]):
        loss += torch.sum(torch.square(targets[i] - pred[i]) * weights) 

    return loss / (pred.shape[0] * 36 ** 2)

# Overlap metric for learned orbital coefficients
def overlap_loss(pred, targets, refs, overlaps, indices):
    pred = pred.reshape(-1, 36, 36)
    targets = targets.reshape(-1, 36, 36)
    overlaps = overlaps.reshape(-1, 36, 36)

    batch_size = pred.shape[0]
    loss = 0
    for i in range(batch_size):
        loss += overlap(pred[i], targets[i], overlaps[i])
    return loss


"""
Loss functions for learned Orbital Transformation Matrix - matrix U
"""
# MSE for learned orbital rotations
def rotated_mse(pred, targets, refs, basis_set_size):
    pred = pred.reshape(-1, basis_set_size, basis_set_size)
    targets = targets.reshape(-1, basis_set_size, basis_set_size)
    refs = refs.reshape(-1, basis_set_size, basis_set_size)
    
    batch_size = pred.shape[0]

    loss = 0
    for i in range(batch_size):
        X = 0.5 * (pred[i] - pred[i].T)
        preds = torch.matmul(torch.linalg.matrix_exp(X), refs[i])
        loss += torch.sum(torch.square(targets[i].flatten() - preds.flatten())) / len(preds.flatten()) 

    return loss / batch_size

# dot product for learned orbital rotations
def rotated_dot_product(pred, targets, refs, overlaps, indices):
    pred = pred.reshape(-1, 36, 36)
    targets = targets.reshape(-1, 36, 36)
    refs = refs.reshape(-1, 36, 36)
    
    batch_size = pred.shape[0]

    loss = 0
    for i in range(batch_size):
        X = 0.5 * (pred[i] - pred[i].T)
        preds = torch.matmul(torch.linalg.matrix_exp(X), refs[i].reshape(-1, 36)).flatten()

        loss += torch.dot(targets[i], preds)

    return loss / (batch_size * 36) 

# Wavefunction overlap metric for learned orbital rotations
def rotated_overlap(pred, targets, refs, overlaps, indices):
    pred = pred.reshape(-1, 36, 36)
    targets = targets.reshape(-1, 36, 36)
    refs = refs.reshape(-1, 36, 36)
    
    batch_size = pred.shape[0]

    loss = 0
    for i in range(batch_size):
        X = 0.5 * (pred[i] - pred[i].T)
        preds = torch.matmul(torch.linalg.matrix_exp(X), refs[i].reshape(-1, 36)).flatten()

        loss += overlap(preds, targets[i], overlaps[i])

    return loss / (batch_size * 36)

# Wavefuction projection metric for learned orbital rotations
def rotated_projection(pred, targets, refs, indices, overlaps, guess_occs, conv_occs):
    pred = pred.reshape(-1, torch.sum(torch.arange(36)))
    targets = targets.reshape(-1, 36**2)
    refs = refs.reshape(-1, 36**2)
    overlaps = overlaps.reshape(-1, 36, 36)
    guess_occs = guess_occs.reshape(-1, 36)
    conv_occs = conv_occs.reshape(-1, 36)
    
    batch_size = pred.shape[0]
    loss = 0
    for i in range(batch_size):
        X = 0.5 * (pred[i] - pred[i].T)
        preds = torch.matmul(torch.linalg.matrix_exp(X), refs[i].reshape(-1, 36))

        loss += 1 / projection(preds, targets[i].reshape(-1, 36), overlaps[i], guess_occs[i], conv_occs[i])
    
    return loss / batch_size


""" 
Loss functions for learned Hamiltonian/Fock operator matrices - H matrix
"""
# MSE for hamiltonian
def hamiltonian_mse(pred, targets, basis_set_size):
    pred = pred.reshape(-1, basis_set_size, basis_set_size)
    targets = targets.reshape(-1, basis_set_size, basis_set_size)

    batch_size = pred.shape[0]
    loss = 0
    for i in range(batch_size):
        H = 0.5 * (pred[i] + pred[i].T)
        loss += torch.sum(torch.square(targets[i].flatten() - H.flatten())) / len(targets[i].flatten())
    return loss / batch_size

def hamiltonian_mse_energies(pred, targets, overlaps, energies):
    pred = pred.reshape(-1, 36, 36)
    targets = targets.reshape(-1, 36, 36)
    overlaps = overlaps.reshape(-1, 36, 36)
    energies = energies.reshape(-1, 36)

    batch_size = pred.shape[0]
    loss = 0
    for i in range(batch_size):
        H = 0.5 * (pred[i] + pred[i].T)
        loss += torch.sum(torch.square(targets[i].flatten() - H.flatten())) / len(targets[i].flatten())

        S = overlaps[i]
        e_s, U = torch.linalg.eig(S)
        diag_s = torch.diag(e_s ** -0.5)
        X = torch.matmul(U, torch.matmul(diag_s, U.T))
        print(X.dtype)
        F_prime = torch.matmul(X.T, torch.matmul(H.type(torch.cfloat), X))
        evals_prime, _ = torch.linalg.eig(F_prime)

        loss += torch.sum(torch.square(energies[i].flatten() - evals_prime.flatten())) / len(evals_prime.flatten())

    return loss / batch_size

# MO energy loss for hamiltonian
def mo_energy_loss(pred, targets, ref, overlaps, indices):
    pred = pred.reshape(-1, 36, 36)
    targets = targets.reshape(-1, 36, 36)
    overlaps = overlaps.reshape(-1, 36, 36)

    batch_size = pred.shape[0]
    loss = 0
    for i in range(batch_size):
        H = 0.5 * (pred[i] + pred[i].T)
        loss += total_mo_energy(H, targets[i], overlaps[i])
    return loss / batch_size