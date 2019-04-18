// ====================================================================== 
// \title  UdpSender/test/ut/Tester.hpp
// \author tcanham
// \brief  hpp file for UdpSender test harness implementation class
//
// \copyright
// Copyright 2009-2015, by the California Institute of Technology.
// ALL RIGHTS RESERVED.  United States Government Sponsorship
// acknowledged. Any commercial use must be negotiated with the Office
// of Technology Transfer at the California Institute of Technology.
// 
// This software may be subject to U.S. export control laws and
// regulations.  By accepting this document, the user agrees to comply
// with all U.S. export laws and regulations.  User has the
// responsibility to obtain export licenses, or other export authority
// as may be required before exporting such information to foreign
// countries or providing access to foreign persons.
// ====================================================================== 

#ifndef TESTER_HPP
#define TESTER_HPP

#include "GTestBase.hpp"
#include "Svc/UdpSender/UdpSenderComponentImpl.hpp"

namespace Svc {

  class Tester :
    public UdpSenderGTestBase
  {

      // ----------------------------------------------------------------------
      // Construction and destruction
      // ----------------------------------------------------------------------

    public:

      //! Construct object Tester
      //!
      Tester(void);

      //! Destroy object Tester
      //!
      ~Tester(void);

    public:

      // ---------------------------------------------------------------------- 
      // Tests
      // ---------------------------------------------------------------------- 

      //! open socket test
      //!
      void openTest(const char* server, const char* port);

      //! open socket test
      //!
      void sendTest(const char* server, const char* port);

    private:

      // ----------------------------------------------------------------------
      // Helper methods
      // ----------------------------------------------------------------------

      //! Connect ports
      //!
      void connectPorts(void);

      //! Initialize components
      //!
      void initComponents(void);

    private:

      // ----------------------------------------------------------------------
      // Variables
      // ----------------------------------------------------------------------

      //! The component under test
      //!
      UdpSenderComponentImpl component;

      void textLogIn(
                const FwEventIdType id, //!< The event ID
                Fw::Time& timeTag, //!< The time
                const Fw::TextLogSeverity severity, //!< The severity
                const Fw::TextLogString& text //!< The event string
            );

      NATIVE_INT_TYPE m_recvFd;
      void udpRecvStart(const char* port);
      NATIVE_INT_TYPE udpGet(U8* buff, NATIVE_UINT_TYPE size);

  };

} // end namespace Svc

#endif