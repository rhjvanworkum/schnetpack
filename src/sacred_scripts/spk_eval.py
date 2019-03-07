import os
from sacred import Experiment
from schnetpack.sacred.evaluator_ingredient import evaluator_ing,\
    build_evaluator


eval_ex = Experiment('evaluation', ingredients=[evaluator_ing])


@eval_ex.config
def config():
    out_path = './results.db'
    model_path = './training/best_model'
    device = 'cpu'


@eval_ex.command
def evaluate(_log, model_path, out_path, device):
    _log.info('build evaluator...')
    evaluator = build_evaluator(model_path=model_path, out_path=out_path)
    _log.info('evaluating...')
    evaluator.evaluate(device=device)


@eval_ex.automain
def main():
    print(eval_ex.config)
