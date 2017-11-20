import os
import numpy as np
import numpy.ma as npm

if 'GDAL_DATA' not in os.environ:
    os.environ['GDAL_DATA'] = r'/usr/lib/anaconda/share/gdal'
import gdal, ogr, osr


DIM_CODES = {
    't': 0,
    's':(1,2),
    'h':1,
    'x':1,
    'we':1,
    'ew':1,
    'v':2,
    'y':2,
    'ns':2,
    'sn':2
    }
    
def _chooseRandom(A, axis, keepdims='Unused', weights=None):
    sh = A.shape
    A = A.reshape((sh[0], -1))
    
    if weights is None:
        p = (1.0-A.mask)
    else:
        p = (1.0-A.mask) * weights
    p = p / p.sum()
    
    if axis == 0:
        # Reduce Temporal
        selections = np.random.choice(A.shape[0], size=A.shape[1], p=p)
        A = A[selections, range(A.shape[1])]
        A = A.reshape((1,sh[1],sh[2]))
    else: #axis = (1,2)
        # Reduce Spatial
        selections = np.random.choice(A.shape[1], size=A.shape[0], p=p)
        A = A[range(A.shape[0]), selections]
        A = A.reshape((sh[0], 1,1))
        
    return A
    
def _overengineeredChooseRandom(data, axis, keepdims=True):
    n = data.ndim
    sh = data.shape
    new_shape = sh
    new_shape[axis] = 1
    
    if not hasattr(axis, 'iter'):
        axis = [axis]

    for a in axis:   
        # Swap axes into front and reshape into table
        data = data.swapaxes(0,a)
        sh = data.shape
        data = data.reshape((sh[0],-1))
        
        # Select one of each column
        selections = np.random.choice(data.shape[0], size=data.shape[1])
        data = data[selections, range(data.shape[1])]
        
        # Reshape back, swap axes back
        data = data.reshape([1]+list(sh)[1:])
        data = data.swapaxes(a,0)
    
    
def _std(A, axis=0, keepdims=True, weights=None):
    if weights is None:
        return npm.std(A, axis=axis, keepdims=keepdims)
    else:
        return npm.sqrt(_var(A, axis=axis, keepdims=keepdims, weights=weights))
        
    
def _var(A, axis=0, keepdims=True, weights=None):
    if weights is None:
        return npm.var(A, axis=axis, keepdims=keepdims)
    else:
        mu = npm.average(A, axis=axis, keepdims=keepdims, weights=weights)
        w = npm.sum(weights, axis=axis, keepdims=keepdims)
        var = npm.sum( weights*(A-mu)**2, axis=axis, keepdims=keepdims, weights=weights) / w**2
        return var
        
def _weighted_median(A, W):
    J = np.argsort(A)
    B = A[J]
    W = weights[J]
    s = np.sum(W)/2
    cs = 0
    for n in range(len(W)):
        cs += W[n]
        if cs > s:
            return B[n]
        if cs == s: 
            return (B[n]+B[n+1])/2
    
    return 0
        
        
def _median(A, axis=0, keepdims=True, weights=None):
    if weights is None:
        return npm.median(A, axis=axis, keepdims=keepdims)
    else:
        sh = A.shape
        A = A.reshape((sh[0], -1))
    
        if axis == 0:
            # Reduce Temporal (with a optimization for the common case of all spatial-weights being the same for each time step)
            med = npm.median(A, axis=0)
            M = np.not_equal(weights[0,:,:] , np.bitwise_and.reduce(weights, axis=0))
            D = A[:,M]
                
            # Only loop throught those that have different weights in each time step
            for j in range(D.shape[1]):
                med[j] = _weighted_median(D[:,j], weights[:,j])
                
            med = med.reshape((1,sh[1],sh[2]))

        else: #axis = (1,2)
            # Reduce Spatial
            med = np.zeros((sh[0]))
            for i in range(sh[0]):
                med[i] = _weighted_median(A[i,:], weights[i,:])
                
            med = med.reshape((sh[0],1,1))
        
        return med

        
def _min(A, axis=0, keepdims=True, weights=None):
    # Weights don't matter
    return npm.min(A, axis=axis, keepdims=keepdims)
    
def _max(A, axis=0, keepdims=True, weights=None):
    # Weights don't matter
    return npm.max(A, axis=axis, keepdims=keepdims)
    
    
    
   
REDUCERS = {
    'mean': npm.average,
    'std':  _std,
    'var': _var,
    'median': _median,
    'min': _min,
    'max': _max,
    'random': _chooseRandom
}    
def apply(R, data, weights=None):

    if not hasattr(R, 'iter'):
        R = [R]
    
    if data.ndim == 2:
        data = data.reshape((1, data.shape[0], data.shape[1]))

    for r in R:
        r = r.split('_')
        if len(r) == 1:
            reducer = r[0]
            dim = None
        else:
            reducer = r[1]
            try:
                dim = DIM_CODES[r[0]]
            except KeyError:
                dim = None
            
        #try:
        
        reducer = REDUCERS[reducer]
        
        #except KeyError:
        #    reducer = REDUCERS['mean']

    
        data = reducer(data, weights=weights, axis=dim, keepdims=True)
    
    return data

