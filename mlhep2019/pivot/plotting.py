import numpy as np
import torch

import matplotlib.pyplot as plt

__all__ = [
  'make_grid',
  'draw_response',

  'nuisance_prediction_hist',
  'nuisance_metric_plot'
]

def make_grid(data, size=25):
  data_min, data_max = np.min(data, axis=0), np.max(data, axis=0)
  delta = data_max - data_min

  xs = np.linspace(data_min[0] - 0.05 * delta[0], data_max[0] + 0.05 * delta[0], num=size)
  ys = np.linspace(data_min[1] - 0.05 * delta[1], data_max[1] + 0.05 * delta[1], num=size)

  grid_X, grid_Y = np.meshgrid(xs, ys)

  grid = np.stack([grid_X.reshape(-1), grid_Y.reshape(-1)]).astype('float32').T
  return xs, ys, grid

def draw_response(xs, ys, probabilities, data, labels):
  probabilities = probabilities.reshape(ys.shape[0], xs.shape[0])

  plt.contourf(xs, ys, probabilities, levels=np.linspace(0, 1, num=20), cmap=plt.cm.plasma)

  plt.scatter(data[labels > 0.5, 0], data[labels > 0.5, 1])
  plt.scatter(data[labels < 0.5, 0], data[labels < 0.5, 1])

  plt.contour(xs, ys, probabilities, levels=[0.5], colors=['black'], linewidths=[3], linestyles=['dashed'])

def nuisance_prediction_hist(predictions, nuisance, names=None, nuisance_bins=20, prediction_bins=20):
  """
  Plots distribution of predictions against nuisance parameter.

  :param predictions: a tuple of 1D numpy arrays containing predictions of models;
  :param nuisance: a 1D numpy array containing values of the nuisance parameter;
  :param names: names of the models;
  :param nuisance_bins: number of bins for the nuisance parameter, ignored if `nuisance` is an array of an integer type;
  :param prediction_bins: number of bins for the predictions.
  :return:
  """
  from .utils import mutual_information

  if nuisance.dtype.kind == 'i':
    nuisance_bins = np.max(nuisance) + 1
    nu_bins=np.arange(nuisance_bins + 1) - 0.5
  else:
    delta = np.max(nuisance) - np.min(nuisance)
    nu_bins=np.linspace(np.min(nuisance) - 1e-3 * delta, np.max(nuisance) + 1e-3 * delta, num=nuisance_bins + 1)

  p_bins = np.linspace(0, 1, num=prediction_bins)

  hists = [
    np.histogram2d(proba, nuisance, bins=(p_bins, nu_bins))[0]
    for proba in predictions
  ]

  plt.subplots(nrows=nuisance_bins, ncols=len(predictions), figsize=(5 * len(predictions), 2 * nuisance_bins))

  for j, _ in enumerate(predictions):
    mi = mutual_information(hists[j])

    for i in range(nuisance_bins):
      plt.subplot(nuisance_bins, len(predictions), i * len(predictions) + j + 1)
      plt.plot(
        (p_bins[1:] + p_bins[:-1]) / 2,
        hists[j][:, nuisance_bins - i - 1]
      )

      if i == 0:
        if names is not None:
          plt.title('%s (MI=%.2e)' % (names[j], mi))
        else:
          plt.title('Model %d (MI=%.2e)' % (j, mi))

def nuasance_predictions_plot(model, data, nuisance):
  from .utils import mutual_information

  p = torch.sigmoid(model(data)).cpu().detach().numpy()

  p_bins = np.linspace(np.min(p), np.max(p), num=21)
  nu_bins = np.arange(6)
  hist, _, _ = np.histogram2d(p, nuisance, bins=(p_bins, nu_bins))
  pmf = hist / np.sum(hist)

  mi = mutual_information(hist)

  plt.imshow(pmf.T, extent=[np.min(p), np.max(p), 0, 5], aspect='auto')
  plt.title('MI = %.2e' % (mi,))
  plt.colorbar()
  plt.xlabel('Network predictions')
  plt.ylabel('Nuisance parameter')

def nuisance_metric_plot(predictions, labels, nuisance, metric_fn, base_level=0.5, names=None, nuisance_bins=10):
  from .utils import binarize

  indx, nu_bins = binarize(nuisance, nuisance_bins)

  metrics = []

  labels_binned = [
    list()
    for _ in range(nu_bins.shape[0] - 1)
  ]
  for i in range(labels.shape[0]):
    labels_binned[indx[i]].append(labels[i])

  labels_binned = [
    np.where(np.array(ls) > 0.5, 1, 0)
    for ls in labels_binned
  ]

  for proba in predictions:
    proba_binned = [
      list()
      for _ in range(nu_bins.shape[0] - 1)
    ]

    for i in range(proba.shape[0]):
      bin_i = indx[i]
      proba_binned[bin_i].append(proba[i])

    proba_binned = [ np.array(ps, dtype='float32') for ps in proba_binned ]

    metric = np.array([
      metric_fn(ls, np.array(pred))
      for pred, ls  in zip(proba_binned, labels_binned)
    ])

    metrics.append(metric)

  for i, metric in enumerate(metrics):
    plt.plot(
      (nu_bins[:-1] + nu_bins[1:]) / 2, metric,
      label=(names[i] if names is not None else None)
    )

  m_min = min([ np.min(metric) for metric in metrics ])
  m_max = max([ np.max(metric) for metric in metrics ])
  m_delta = m_max - m_min

  plt.ylim([min(m_min, base_level), m_max + 0.05 * m_delta ])
  plt.ylabel('metric')
  plt.xlabel('nuisance parameter')

  if names is not None:
    plt.legend()