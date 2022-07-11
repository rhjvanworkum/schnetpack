import logging
import pytorch_lightning
import torchmetrics
from pytorch_lightning.loggers import WandbLogger
from sklearn.metrics import log_loss
import src.schnetpack as spk
import schnetpack.transform as trn

from models.loss_functions import rotated_mse, mo_energy_loss, hamiltonian_mse, hamiltonian_mse_energies
from models.orbital_model import get_orbital_model

model_name = 'geom_scan_199_molcas_fock_painn_noncan'
database = './data/geom_scan_199_molcas_fock_noncan.db'
split_file = './data/geom_scan_199.npz'

cutoff = 5.0
basis_set_size = 36
property = 'F'

epochs = 100
batch_size = 16
lr = 5e-4

""" Initializing a dataset """
dataset = spk.data.AtomsDataModule(
  datapath=database,
  batch_size=batch_size,
  split_file=split_file,
  transforms=[
    trn.ASENeighborList(cutoff=5.),
    trn.CastTo32()
  ],
  property_units={property: 1.0, 'overlap': 1.0, 'energies': 1.0},
  num_workers=0,
  pin_memory=True,
  load_properties=[property, 'overlap', 'energies']
)

""" Initiating the Model """
model = get_orbital_model(loss_fn=hamiltonian_mse, loss_type="", lr=lr, output_key=property)

""" Just for testing purposes """
# dataset.setup()
# for idx, sample in enumerate(dataset.train_dataloader()):
#   # output = model(sample)
#   loss = model.training_step(sample, 0)
#   # loss = model.training_step(sample, 1)
#   print(loss)
#   break


# callbacks for PyTroch Lightning Trainer
logging.info("Setup trainer")
callbacks = [
    spk.train.ModelCheckpoint(
        monitor="val_loss",
        mode="min",
        save_top_k=1,
        save_last=True,
        dirpath="checkpoints",
        filename="{epoch:02d}",
        inference_path="./checkpoints/" + model_name + ".pt"
    ),
    # pytorch_lightning.callbacks.EarlyStopping(
    #     monitor="val_loss", patience=150, mode="min", min_delta=0.0
    # ),
    pytorch_lightning.callbacks.LearningRateMonitor(logging_interval="epoch"),
]

logger = WandbLogger(project="excited-state-orbitals")
trainer = pytorch_lightning.Trainer(callbacks=callbacks, 
                                    logger=logger,
                                    default_root_dir='./test/',
                                    max_epochs=epochs)

logging.info("Start training")
trainer.fit(model, datamodule=dataset)