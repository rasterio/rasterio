#ifndef _RIO_PYVSI_HANDLE_H_
#define _RIO_PYVSI_HANDLE_H_

#include "cpl_vsi_virtual.h"

namespace pyvsi_handle {

class PythonVSIVirtualHandle : public VSIVirtualHandle {
  public:
    PyObject  *open_file_obj = nullptr;

    // VSIVirtualHandle Overrides
    int       Seek( vsi_l_offset nOffset, int nWhence );
    vsi_l_offset Tell();
    size_t    Read( void *pBuffer, size_t nSize, size_t nCount );
    int       ReadMultiRange( int nRanges, void ** ppData,
                              const vsi_l_offset* panOffsets,
                              const size_t* panSizes );
    size_t    Write( const void *pBuffer, size_t nSize, size_t nCount);
    int       Eof();
    int       Flush() {return 0;}
    int       Close();
    // Base implementation that only supports file extension.
    int       Truncate( vsi_l_offset nNewSize );
    void     *GetNativeFileDescriptor() { return nullptr; }
    VSIRangeStatus GetRangeStatus( CPL_UNUSED vsi_l_offset nOffset,
                                   CPL_UNUSED vsi_l_offset nLength )
                                  { return VSI_RANGE_STATUS_UNKNOWN; }

    PythonVSIVirtualHandle(PyObject *obj);
    ~PythonVSIVirtualHandle();
};

VSILFILE *CreatePyVSIInMem(const char *pszFilename, PythonVSIVirtualHandle *handle);

} /* namespace pyvsi_handle */
#endif /* _RIO_PYVSI_HANDLE_H_ */