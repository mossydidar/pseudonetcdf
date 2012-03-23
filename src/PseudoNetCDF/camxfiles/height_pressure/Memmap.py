__all__=['height_pressure']
__doc__ = """
.. _Memmap
:mod:`Memmap` -- height/pressure Memmap interface
=================================================

.. module:: Memmap
   :platform: Unix, Windows
   :synopsis: Provides :ref:`PseudoNetCDF` memory map for CAMx
              height/pressure files.  See PseudoNetCDF.sci_var.PseudoNetCDFFile 
              for interface details
.. moduleauthor:: Barron Henderson <barronh@unc.edu>
"""
HeadURL="$HeadURL: http://dawes.sph.unc.edu:8080/uncaqmlsvn/pyPA/utils/trunk/CAMxMemmap.py $"
ChangeDate = "$LastChangedDate$"
RevisionNum= "$LastChangedRevision$"
ChangedBy  = "$LastChangedBy: svnbarronh $"
__version__ = RevisionNum

#Distribution packages
import unittest
import struct

#Site-Packages
from numpy import zeros,array,where,memmap,newaxis,dtype,nan

#This Package modules
from PseudoNetCDF.camxfiles.FortranFileUtil import OpenRecordFile,Int2Asc
from PseudoNetCDF.sci_var import PseudoNetCDFFile, PseudoNetCDFVariable, PseudoNetCDFVariables
from PseudoNetCDF.ArrayTransforms import ConvertCAMxTime

#for use in identifying uncaught nan
listnan=struct.unpack('>f','\xff\xc0\x00\x00')[0]
checkarray=zeros((1,),'f')
checkarray[0]=listnan
array_nan=checkarray[0]
    
class height_pressure(PseudoNetCDFFile):
    """
    height_pressure provides a PseudoNetCDF interface for CAMx
    height_pressure files.  Where possible, the inteface follows
    IOAPI conventions (see www.baronams.com).
    
    ex:
        >>> height_pressure_path = 'camx_height_pressure.bin'
        >>> rows,cols = 65,83
        >>> height_pressurefile = height_pressure(height_pressure_path,rows,cols)
        >>> height_pressurefile.variables.keys()
        ['TFLAG', 'HGHT', 'PRES']
        >>> v = height_pressurefile.variables['V']
        >>> tflag = height_pressurefile.variables['TFLAG']
        >>> tflag.dimensions
        ('TSTEP', 'VAR', 'DATE-TIME')
        >>> tflag[0,0,:]
        array([2005185,       0])
        >>> tflag[-1,0,:]
        array([2005185,  240000])
        >>> v.dimensions
        ('TSTEP', 'LAY', 'ROW', 'COL')
        >>> v.shape
        (25, 28, 65, 83)
        >>> height_pressurefile.dimensions
        {'TSTEP': 25, 'LAY': 28, 'ROW': 65, 'COL': 83}
    """
    
    id_fmt='fi'
    data_fmt='f'
    def __init__(self,rf,rows=None,cols=None):
        self.__memmap=memmap(rf,'>f','r',offset=0)
        rowsXcols=self.__memmap[0].view('i')/4-2
        record_length=rowsXcols+4
        records=self.__memmap.size/record_length
        
        times=self.__memmap.reshape(records,record_length)[:,1:3]
        self.STIME,self.SDATE=times[0]
        for i,(t,d) in enumerate(times):
            if (t,d)!=(self.STIME,self.SDATE):
                break
        self.SDATE=self.SDATE.view('i')
        self.createDimension('LAY',i/2)
        self.createDimension('TSTEP',times.shape[0]/i)
        
        if rows==None and cols==None:
            rows=rowsXcols
            cols=1
        elif rows==None:
            rows=rowsXcols/cols
        elif cols==None:
            cols=rowsXcols/rows
        else:
            if cols*rows!=rowsXcols:
                raise ValueError, "The product of cols (%d) and rows (%d) must equal cells (%d)" %  (cols,rows,rowsXcols)
        
        self.createDimension('ROW',rows)
        self.createDimension('COL',cols)
        self.createDimension('DATE-TIME',2)
        self.createDimension('VAR',2)

        self.NROWS=rows
        self.NCOLS=cols
        self.NLAYS=len(self.dimensions['LAY'])
        self.NVARS=2
        self.NTHIK=1

        setattr(self,'VAR-LIST','HGHT'.ljust(16)+'PRES'.ljust(16))
        
        self.variables=PseudoNetCDFVariables(self.__var_get,['HGHT','PRES','TFLAG'])
    
    def __var_get(self,key):
        lays=len(self.dimensions['LAY'])
        times=len(self.dimensions['TSTEP'])
        rows=len(self.dimensions['ROW'])
        cols=len(self.dimensions['COL'])
        hght=1
        pres=2
        time=3
        date=4
        out_idx=zeros(self.__memmap.shape,dtype='b').reshape(times,lays,2,rows*cols+4)
        out_idx[:,:,0,3:-1]=hght
        out_idx[:,:,1,3:-1]=pres
        out_idx[:,:,:,1]=time
        out_idx[:,:,:,2]=date
        out_idx=out_idx.ravel()
        buf=self.__memmap[out_idx==0].reshape(lays*2*times,2)
        if not (buf[:,0]==buf[:,1]).all():
            raise ValueError,"Buffer"
        v=self.variables['HGHT']=PseudoNetCDFVariable(self,'HGHT','f',('TSTEP','LAY','ROW','COL'),values=self.__memmap[out_idx==1].reshape(times,lays,rows,cols))
        v.units='m'
        v.long_name='HGHT'.ljust(16)
        v.var_desc='Top Height'
        v=self.variables['PRES']=PseudoNetCDFVariable(self,'PRES','f',('TSTEP','LAY','ROW','COL'),values=self.__memmap[out_idx==2].reshape(times,lays,rows,cols))
        v.units='hPA'
        v.long_name='PRES'.ljust(16)
        v.var_desc='Pressure at center'
        self.variables['TFLAG']=ConvertCAMxTime(self.__memmap[out_idx==4][slice(None,None,len(self.dimensions['LAY'])*2)].view('>i'),self.__memmap[out_idx==3][slice(None,None,len(self.dimensions['LAY'])*2)],len(self.dimensions['VAR']))
        
        return self.variables[key]

class TestMemmap(unittest.TestCase):
    def runTest(self):
        pass
    def setUp(self):
        pass

    def testHP(self):
        import PseudoNetCDF.testcase
        hpfile=height_pressure(PseudoNetCDF.testcase.CAMxHeightPressure,65,83)
        hpfile.variables['TFLAG']
        self.assert_((hpfile.variables['HGHT'].mean(0).mean(1).mean(1)==array([    33.890625  ,     84.93463135,    170.56620789,    256.90753174,
          343.97067261,    431.7701416 ,    520.31616211,    609.62701416,
          699.71228027,    790.59112549,    928.42340088,   1068.12695312,
         1209.74743652,   1353.35302734,   1597.25683594,   1847.13049316,
         2103.29101562,   2366.0949707 ,   2690.75830078,   3026.26611328,
         3373.41748047,   4106.40332031,   4898.45361328,   5836.37402344,
         6961.35107422,   9166.87207031,  13057.72558594,  15177.14160156],dtype='f')).all())

               
if __name__ == '__main__':
    unittest.main()
