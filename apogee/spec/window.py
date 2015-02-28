###############################################################################
# apogee.spec.window: routines for dealing with the individual element windows
###############################################################################
import os, os.path
import numpy
from apogee.tools.read import modelspecOnApStarWavegrid
_MINWIDTH= 3.5 #minimum width of a window in \AA

def path(elem):
    """
    NAME:
       path
    PURPOSE:
       return the path of a window file
    INPUT:
       elem - element
    OUTPUT:
       path string
    HISTORY:
       2015-02-27 - Written - Bovy (IAS)
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'filter/%s.filt' \
                                       % ((elem.lower().capitalize())))
@modelspecOnApStarWavegrid
def read(elem,apStarWavegrid=True):
    """
    NAME:
       read
    PURPOSE:
       read the window weights for a given element
    INPUT:
       elem - element
       apStarWavegrid= (True) if True, output the window onto the apStar wavelength grid, otherwise just give the ASPCAP version (blue+green+red directly concatenated)
    OUTPUT:
       Array with window weights
    HISTORY:
       2015-01-25 - Written - Bovy (IAS)
    """
    return numpy.loadtxt(path(elem))

def num(elem,pad=0):
    """
    NAME:
       num
    PURPOSE:
       return the number of windows for a given element or window array
    INPUT:
       elem - element
       pad= (0) pad on each side by this many log10 wavelengths in 6e-6 (changes how windows are combined)
    OUTPUT:
       Number of windows
    HISTORY:
       2015-01-25 - Written - Bovy (IAS)
    """
    # Calculate the wavelength regions
    si, ei= waveregions(elem,asIndex=True,pad=pad)
    return len(si)

def waveregions(elem,asIndex=False,pad=0):
    """
    NAME:
       waveregions
    PURPOSE:
       return the wavelength regions corresponding to different elements
    INPUT:
       elem - element
       asIndx= (False) if yes, return the indices into an apStar-like wavelength grid rather than the wavelengths directly
       pad= (0) pad on each side by this many log10 wavelengths in 6e-6 (changes how windows are combined)
    OUTPUT:
       (startlams,endlams) or (startindxs, endindxs)
    BUGS:
       range that comes out of asIndex=True is (or can be) different from that of asIndex=False
    HISTORY:
       2015-01-26 - Written - Bovy (IAS@KITP)
    """
    # Load the window
    win= read(elem,apStarWavegrid=True)
    # Calculate number of contiguous regions, assume this is not at the edge
    mask= ((win > 0.)*(True-numpy.isnan(win))).astype('int')
    dmaskp= numpy.roll(mask,-1)-mask
    dmaskn= numpy.roll(mask,1)-mask
    # Calculate the distance between adjacent windows and combine them if close
    import apogee.spec.plot as splot
    l10wavs= numpy.log10(splot.apStarWavegrid())
    indices= numpy.arange(len(l10wavs))
    if asIndex:
        startindxs= indices[dmaskp == 1.]
        endindxs= indices[dmaskn == 1.]
    startl10lams= l10wavs[dmaskp == 1.]
    endl10lams= l10wavs[dmaskn == 1.]
    if pad > 0:
        if asIndex:
            startindxs= [si-pad for si in startindxs]
            endindxs= [ei+pad for ei in endindxs]
        startl10lams-= pad*splot._DLOG10LAMBDA
        endl10lams+= pad*splot._DLOG10LAMBDA
    # Check that each window is at least _MINWIDTH wide
    width= 10.**endl10lams-10.**startl10lams
    for ii in range(len(startl10lams)):
        if width[ii] < _MINWIDTH:
            if asIndex: # Approximate
                dindx= int(numpy.ceil((_MINWIDTH-width[ii])/2.\
                                          /(10.**startl10lams[ii]\
                                                +10.**endl10lams[ii])/2.\
                                          /numpy.log(10.)/splot._DLOG10LAMBDA))
                startindxs[ii]-= dindx
                endindxs[ii]+= dindx                   
            startl10lams[ii]= numpy.log10(10.**startl10lams[ii]\
                                              -(_MINWIDTH-width[ii])/2.)
            endl10lams[ii]= numpy.log10(10.**endl10lams[ii]\
                                            +(_MINWIDTH-width[ii])/2.)
    diff= numpy.roll(startl10lams,-1)-endl10lams
    if asIndex:
        newStartindxs, newEndindxs= [startindxs[0]], [endindxs[0]]
    newStartl10lams, newEndl10lams= [startl10lams[0]], [endl10lams[0]]
    winIndx= 0
    for ii in range(len(startl10lams)-1):
        if diff[ii] < 10.*splot._DLOG10LAMBDA:
            if asIndex:
                newEndindxs[winIndx]= endindxs[ii+1]
            newEndl10lams[winIndx]= endl10lams[ii+1]
        else:
            if asIndex:
                newStartindxs.append(startindxs[ii+1])
                newEndindxs.append(endindxs[ii+1])
            newStartl10lams.append(startl10lams[ii+1])
            newEndl10lams.append(endl10lams[ii+1])
            winIndx+= 1
    if asIndex:
        return (newStartindxs,newEndindxs)
    else:
        return (10.**numpy.array(newStartl10lams),
                10.**numpy.array(newEndl10lams))

def tophat(elem):
    """
    NAME:
       tophat
    PURPOSE:
       return an array with True in the window of a given element and False otherwise
    INPUT:
       elem - element     
    OUTPUT:
       array on apStar grid
    HISTORY:
       2015-01-26 - Written - Bovy (IAS@KITP)
    """
    import apogee.spec.plot as splot
    out= numpy.zeros(splot._NLAMBDA,dtype='bool')
    for si,ei in zip(*waveregions(elem,asIndex=True)):
        out[si+1:ei]= True
    return out

def total_dlambda(elem,pad=0):
    """
    NAME:
       total_dlambda
    PURPOSE:
       return the total wavelength span covered by the windows of a given element
    INPUT:
       elem - element     
       pad= (0) pad on each side by this many log10 wavelengths in 6e-6 (changes how windows are combined)
    OUTPUT:
       total width in \AA
    HISTORY:
       2015-01-26 - Written - Bovy (IAS@KITP)
    """
    si,ei= waveregions(elem,asIndex=False,pad=pad)
    return numpy.sum(ei-si)

def equishwidth(elem,spec,specerr,refspec=None):
    """
    NAME:
       equishwidth
    PURPOSE:
       return an equivalent-width-ish quantity for a given element:

       equishwidth = \sum_lam \Delta lam_center of window x (refspec-spec)/refspec x window/specerr^2 / \sum_lam window/specerr^2

       or if refspec == 0:

       equishwidth = \sum_lam \Delta lam_center of window x (1-spec) x window/specerr^2 / \sum_lam window/specerr^2


    INPUT:
       elem - element to consider
       spec - spectrum on apStarWavegrid (nwave)
       specerr - error on the spectrum on apStarWavegrid (nwave)
       refspec= reference spectrum (assumed to be zero if absent)
    OUTPUT:
        equivalent-ish-width
    HISTORY:
       2015-02-11 - Written - Bovy (IAS@KITP)
    """
    if refspec is None:
        refspec= numpy.zeros_like(spec)
    # Read windows
    win= read(elem,apStarWavegrid=True)
    startindxs, endindxs= waveregions(elem,asIndex=True,pad=0)
    import apogee.spec.plot as splot
    lams= splot.apStarWavegrid()
    startlams= lams[startindxs]
    endlams= lams[endindxs]
    outval= 0.
    norm= 0.
    for (startindx,endindx,startlam,endlam) \
            in zip(startindxs,endindxs,startlams,endlams):
        norm+= numpy.sum(win[startindx:endindx]\
                                /specerr[startindx:endindx]**2.)
        if not numpy.all(refspec == 0.):
            outval+= (endlam-startlam)/(endindx-startindx)\
                *numpy.sum(win[startindx:endindx]/specerr[startindx:endindx]**2.\
                               *(1.-spec[startindx:endindx]/refspec[startindx:endindx]))
        else:
            outval+= (endlam-startlam)/(endindx-startindx)\
                *numpy.sum(win[startindx:endindx]/specerr[startindx:endindx]**2.\
                               *(1.-spec[startindx:endindx]))
    outval/= norm
    return outval
