"""
Synthetic HLD Generator
=======================
Creates a realistic-but-clearly-synthetic AUTOSAR HLD PDF for demo/evaluation.

IMPORTANT: This is SYNTHETIC DEMO DATA only.
No confidential Tata Technologies material is included.

Uses reportlab for PDF generation. Falls back to plain text if unavailable.
ASCII-safe text only (avoids Windows cp1252 encoding issues).
"""

from __future__ import annotations
from pathlib import Path

# ===========================================================================
# SYNTHETIC CONTENT (ASCII-safe — no special Unicode arrows/em-dashes)
# ===========================================================================
SYNTHETIC_TEXT = """\
SYNTHETIC DEMO DATA - FOR EVALUATION/DEMO PURPOSES ONLY
This document does not contain any confidential Tata Technologies material.
Generated for the AUTOSAR HLD AI Assistant capstone demonstration.

========================================================================
AUTOSAR HIGH-LEVEL DESIGN DOCUMENT
Project: EV Powertrain Control Unit (PCU) - Demo ECU
Document Number: PCU-HLD-0001
Version: 1.0
Status: SYNTHETIC DEMO - Not for production use
Prepared by: AUTOSAR HLD AI Assistant Demo Team
========================================================================

TABLE OF CONTENTS
1. Introduction
2. System Overview
3. Software Architecture
4. Software Components
5. Interfaces and Ports
6. Signals
7. Dependencies
8. Functional Flows
9. Configuration
10. Known Limitations and Future Work

========================================================================
1. INTRODUCTION
========================================================================

1.1 Purpose
This High-Level Design (HLD) document describes the software architecture
of the EV Powertrain Control Unit (PCU) Demo ECU. It defines the software
components, their responsibilities, interfaces, ports, signals, and
inter-component dependencies following the AUTOSAR Classic Platform
methodology (Release 4.4).

1.2 Scope
This document covers the application layer and Basic Software (BSW) layer
of the PCU Demo ECU. Hardware-specific details and hardware schematics
are out of scope for this document.

1.3 Applicable Standards
- AUTOSAR Classic Platform Release 4.4
- ISO 26262 Functional Safety (reference only)
- ISO 14229 Unified Diagnostic Services (UDS)
- ISO 15765-2 CAN transport layer

1.4 Abbreviations and Acronyms
- SWC:  Software Component
- BSW:  Basic Software
- MCAL: Microcontroller Abstraction Layer
- RTE:  Runtime Environment
- PDU:  Protocol Data Unit
- NvM:  Non-volatile Memory Manager
- DCM:  Diagnostic Communication Manager
- DEM:  Diagnostic Event Manager
- ECU:  Electronic Control Unit
- CAN:  Controller Area Network
- UDS:  Unified Diagnostic Services
- PWM:  Pulse Width Modulation
- PduR: PDU Router
- CanIf: CAN Interface
- BswM: BSW Mode Manager

1.5 Document History
Version 1.0 - Initial release - Synthetic Demo Document

========================================================================
2. SYSTEM OVERVIEW
========================================================================

2.1 System Context
The PCU Demo ECU is responsible for managing powertrain control functions
including motor torque control, diagnostic session management, fault
detection and reporting, and firmware update capabilities via the CAN
diagnostic interface.

2.2 AUTOSAR Layered Architecture
The PCU follows the standard AUTOSAR Classic layered model:
  Layer 1: Application Layer (Application SWCs)
    - DiagnosticManager (DCM_SWC)
    - FlashManager (Flash_SWC)
    - MotorControlSWC (MotCtrl_SWC)
  Layer 2: Runtime Environment (RTE)
    - Mediates all inter-component communication
    - Port-based sender/receiver and client/server patterns
  Layer 3: Basic Software (BSW)
    - Service Layer: NvMManager, ECUStateManager, CommunicationManager
    - ECU Abstraction Layer: CanIf, PduR
    - Microcontroller Abstraction Layer (MCAL): CANDriver, FlashDriver
  Layer 4: Microcontroller (Hardware)

2.3 Hardware Platform (Synthetic/Demo)
- Processor: ARM Cortex-M7 (Demo - Synthetic specification)
- CAN Controllers: 2x (HS-CAN at 500 kbps, MS-CAN at 125 kbps)
- Flash Memory: 4 MB total (3 MB application, 1 MB bootloader)
- RAM: 512 KB total
- EEPROM: 64 KB for NvM data

2.4 Communication Overview
The PCU communicates externally via two CAN networks:
- HS-CAN (High Speed): Diagnostic and main vehicle bus
- MS-CAN (Medium Speed): Body control and comfort functions

External diagnostic tools connect via the HS-CAN OBD-II connector using
UDS protocol (ISO 14229) over CAN transport (ISO 15765-2).

========================================================================
3. SOFTWARE ARCHITECTURE
========================================================================

3.1 Architecture Pattern
The PCU uses a component-based AUTOSAR Classic architecture. All
inter-component communication is mediated by the RTE (Runtime Environment).
Components communicate ONLY through RTE ports - direct function calls
between application SWCs are not permitted.

3.2 Component Interaction Overview
DiagnosticManager <-> CANDriver (via PduR and CanIf layers)
DiagnosticManager <-> NvMManager (for fault storage and DID data)
FlashManager <-> NvMManager (for programming status persistence)
FlashManager <-> DiagnosticManager (reprogramming trigger via UDS)
ECUStateManager <-> all BSW modules (lifecycle coordination)
CommunicationManager <-> CANDriver (CAN bus state management)
MotorControlSWC <-> DiagnosticManager (fault inhibit signal)
MotorControlSWC <-> ECUStateManager (run mode permission)

3.3 Port Communication Types
- Sender-Receiver: Asynchronous signal exchange (e.g. motor torque signal)
- Client-Server: Synchronous operation call (e.g. NvM read/write)
- Mode-Switch: ECU state changes (e.g. ECUStateManager mode port)

3.4 RTE Mapping and Task Scheduling
The OS task mapping is defined in the RTE configuration:
- Task_1ms:   MotorControlSWC_MainFunction (motor control loop)
- Task_5ms:   ECUStateManager_MainFunction (state machine)
- Task_10ms:  DiagnosticManager_MainFunction, CommunicationManager_MainFunction
- Task_100ms: NvMManager_MainFunction, FlashManager_MainFunction (idle)
- Task_Background: Low-priority housekeeping tasks

========================================================================
4. SOFTWARE COMPONENTS
========================================================================

4.1 DiagnosticManager (DCM_SWC)
Type: Application SWC
Layer: Application Layer
AUTOSAR Category: NvBlockSwComponent
Cyclic Period: 10ms (Task_10ms)

Responsibility:
The DiagnosticManager (DCM_SWC) manages UDS (ISO 14229) diagnostic
sessions for the PCU ECU. It processes incoming diagnostic requests
from external testers received via the CAN bus and generates
diagnostic responses. It manages diagnostic session states (Default,
Extended, Programming) and security access levels (Locked, Unlocked).
It interfaces with the DEM (Diagnostic Event Manager) for fault event
reporting and with the NvMManager for reading and writing diagnostic
data records (DIDs) and Freeze Frame data.

Provides (Server ports):
  - Dcm_MainFunction() - periodic main function executed every 10ms
  - Dcm_GetSecurityLevel() - returns current security access level
  - Dcm_GetActiveProtocol() - returns active diagnostic protocol
  - Dcm_TriggerOnEvent() - triggers event-driven diagnostic processing

Required (Client/Receiver ports):
  - CanIf_Transmit() - CAN frame transmission via CAN interface
  - NvM_WriteBlock() - NvM data write for DID storage
  - NvM_ReadBlock() - NvM data read for DID retrieval
  - Dem_SetEventStatus() - fault event reporting to DEM
  - EcuM_RequestRUN() - RUN mode request during diagnostic session

Internal State Machine:
  - DEFAULT_SESSION: Normal ECU operation, limited diagnostics
  - EXTENDED_SESSION: Extended diagnostics, full DID access
  - PROGRAMMING_SESSION: Flash reprogramming enabled

4.2 CANDriver (CAN_MCAL)
Type: MCAL Driver (Basic Software)
Layer: Microcontroller Abstraction Layer (MCAL)
AUTOSAR Category: MCAL

Responsibility:
The CANDriver (CAN_MCAL) provides hardware-abstracted access to the
CAN controller peripheral. It initializes the CAN hardware registers,
controls CAN hardware objects (message buffers) for transmission and
reception, handles CAN interrupts, and reports bus-off conditions and
error states to the CanSM (CAN State Manager). The CANDriver is
compliant with the AUTOSAR CAN Driver specification SWS_CAN_00000.

Provides (API functions):
  - Can_Init() - initializes CAN driver with configuration
  - Can_Write() - requests CAN frame transmission
  - Can_Read() - not used directly (interrupt-driven reception)
  - Can_MainFunction_Write() - periodic transmission handling
  - Can_MainFunction_Read() - periodic reception handling
  - Can_MainFunction_BusOff() - periodic bus-off detection
  - Can_GetControllerState() - returns controller state

Required:
  - MCU clock configuration from MCAL_MCU module
  - DIO port configuration from MCAL_DIO module
  - OS interrupt configuration for CAN receive interrupt

Error Detection:
  - CAN_E_PARAM_POINTER - null pointer parameter
  - CAN_E_UNINIT - module not initialized
  - CAN_E_PARAM_HANDLE - invalid message handle

4.3 FlashManager (Flash_SWC)
Type: Application SWC
Layer: Application Layer
AUTOSAR Category: AtomicSwComponent

Responsibility:
The FlashManager (Flash_SWC) manages the bootloader-assisted flash
programming sequences for ECU software reprogramming. It implements
the flash memory erase, write, and CRC verification operations.
Programming is triggered by the DiagnosticManager when a UDS
RequestDownload service (0x34) is received in Programming Session.
Programming status is persisted to NvMManager after each operation.

Provides (Server ports):
  - Flash_StartProgrammingSequence() - initiates flash erase/write
  - Flash_GetProgrammingStatus() - returns current programming state
  - Flash_VerifyChecksum() - verifies written block CRC

Required (Client/Receiver ports):
  - NvM_WriteBlock() - stores programming status persistently
  - NvM_ReadBlock() - reads previous programming status
  - Fls_Erase() - flash sector erase via Flash MCAL
  - Fls_Write() - flash page write via Flash MCAL
  - Dcm_ProcessRequestDownloadResponse() - UDS download response

Programming State Machine:
  - FLASH_IDLE: No programming in progress
  - FLASH_ERASE: Sector erase in progress
  - FLASH_WRITE: Data write in progress
  - FLASH_VERIFY: CRC verification in progress
  - FLASH_SUCCESS: Programming completed successfully
  - FLASH_FAILED: Programming error occurred

4.4 NvMManager (NvM_BSW)
Type: BSW Service Component
Layer: Service Layer
AUTOSAR Category: ServiceComponent

Responsibility:
The NvMManager (NvM_BSW) provides a unified, hardware-independent
interface for non-volatile data management. It abstracts the underlying
EEPROM and flash memory devices through the MemIf (Memory Abstraction
Interface). All application SWCs that require persistent data storage
access NvMManager instead of directly accessing memory hardware.
NvMManager manages data integrity through CRC and redundant storage.

Provides (Server functions):
  - NvM_WriteBlock() - asynchronous block write request
  - NvM_ReadBlock() - asynchronous block read request
  - NvM_GetErrorStatus() - query operation result
  - NvM_InvalidateNvBlock() - mark block as invalid
  - NvM_EraseNvBlock() - erase NvM block

Required:
  - MemIf_Read() - memory read via abstraction interface
  - MemIf_Write() - memory write via abstraction interface
  - MemIf_GetStatus() - MemIf status query

NvM Blocks defined for PCU:
  - NvM_DiagnosticDTC: Stored DTC data (256 bytes, CRC protected)
  - NvM_CalibrationData: Calibration parameters (512 bytes)
  - NvM_ProgrammingStatus: Flash programming result (16 bytes)
  - NvM_EcuConfig: ECU configuration data (128 bytes)
  - NvM_FreezeFrame: DTC freeze frame data (64 bytes)

4.5 ECUStateManager (EcuM_BSW)
Type: BSW Service Component
Layer: Service Layer
AUTOSAR Category: ServiceComponent

Responsibility:
The ECUStateManager (EcuM_BSW) controls the overall lifecycle of the
PCU ECU. It manages the ECU state machine including STARTUP, RUN,
SLEEP, and SHUTDOWN states. It arbitrates RUN mode requests from all
application SWCs and coordinates the initialization and deinitialization
sequences of all BSW modules. ECUStateManager implements the AUTOSAR
EcuM Fixed state machine (EcuM_State).

Provides (Server ports and mode switch):
  - EcuM_GetState() - returns current ECU state
  - EcuM_RequestRUN() - application SWC requests RUN mode
  - EcuM_ReleaseRUN() - application SWC releases RUN mode
  - EcuM_SelectShutdownTarget() - set shutdown target state
  - EcuM_GetCurrentWakeupSources() - query wakeup sources

Required:
  - ComM_GetCurrentComMode() - communication channel state
  - BswM_RequestMode() - BSW mode management
  - Os_TerminateTask() - OS task termination on shutdown

ECU States:
  - ECUM_STATE_STARTUP_ONE: Pre-OS initialization
  - ECUM_STATE_STARTUP_TWO: Post-OS BSW initialization
  - ECUM_STATE_APP_RUN: Normal application execution
  - ECUM_STATE_APP_POST_RUN: Post-run activities
  - ECUM_STATE_SHUTDOWN: ECU shutdown sequence
  - ECUM_STATE_SLEEP: Low-power sleep mode

4.6 CommunicationManager (ComM_BSW)
Type: BSW Service Component
Layer: Service Layer
AUTOSAR Category: ServiceComponent

Responsibility:
The CommunicationManager (ComM_BSW) manages the communication channel
states for the CAN networks. It coordinates the CAN bus wake-up and
sleep transition sequences and routes communication mode requests from
application SWCs to the underlying network management (NM) layer and
CanSM. It ensures that the CAN bus is available when required by
diagnostic or application communication.

Provides:
  - ComM_RequestComMode() - request communication mode (FULL or NO_COM)
  - ComM_GetCurrentComMode() - query current communication mode
  - ComM_GetMaxComMode() - query highest requested mode

Required:
  - CanSM_RequestComMode() - CAN state machine mode request
  - Nm_NetworkRequest() - network management wakeup request
  - BswM_ComM_CurrentMode() - report mode to BSW mode manager

Communication Modes:
  - COMM_NO_COMMUNICATION: CAN bus in sleep/silent mode
  - COMM_SILENT_COMMUNICATION: Receive only (no transmission)
  - COMM_FULL_COMMUNICATION: Full CAN TX and RX active

4.7 MotorControlSWC (MotCtrl_SWC)
Type: Application SWC
Layer: Application Layer
AUTOSAR Category: AtomicSwComponent
Cyclic Period: 1ms (Task_1ms - highest priority)

Responsibility:
The MotorControlSWC (MotCtrl_SWC) implements the closed-loop torque
control algorithm for the electric traction motor. It reads target
torque setpoints received via CAN from the vehicle controller, monitors
actual torque feedback from the motor current sensors, applies PID
control to generate PWM duty cycle commands to the inverter, and
monitors for motor faults. When a diagnostic fault inhibit signal is
received from DiagnosticManager, the motor torque is set to 0 Nm
for safety.

Provides (Sender ports):
  - MotCtrl_ActualTorque - actual motor torque feedback signal
  - MotCtrl_FaultStatus - motor fault status signal

Required (Receiver ports):
  - MotCtrl_TorqueSetpoint - target torque from vehicle controller
  - Diag_FaultInhibit - fault inhibit from DiagnosticManager
  - EcuM_CurrentState - ECU state from ECUStateManager
  - Pwm_SetDutyCycle() - PWM output to inverter via MCAL

Control Algorithm:
  - Setpoint input: MotCtrl_TorqueSetpoint (range -500 to +500 Nm)
  - Feedback: Motor current measurement via ADC
  - Control: PID controller with anti-windup
  - Output: PWM duty cycle to 3-phase inverter
  - Safety: Zero torque on fault inhibit or ECU not in APP_RUN state

========================================================================
5. INTERFACES AND PORTS
========================================================================

5.1 Interface: Diagnostic Communication Interface
  Name: If_DiagnosticCommunication
  Type: Client-Server
  Provider: DiagnosticManager (DCM_SWC)
  Consumer: External UDS Tester via CAN bus
  Protocol: UDS (ISO 14229) over CAN TP (ISO 15765-2)
  Port Names:
    - Dcm_RequestPort: required port (receives UDS requests from CanIf)
    - Dcm_ResponsePort: provided port (sends UDS responses via CanIf)
    - Dcm_SecurityPort: provided port (security level query)
    - Dcm_SessionPort: provided port (session state query)

5.2 Interface: CAN Hardware Interface
  Name: If_CANHardware
  Type: MCAL API (direct function call)
  Provider: CANDriver (CAN_MCAL)
  Consumer: CanIf (CAN Interface BSW module)
  Port Names:
    - Can_TxPort: hardware object transmit port
    - Can_RxPort: hardware object receive port (interrupt notification)
    - Can_StatePort: controller state notification port

5.3 Interface: NvM Data Interface
  Name: If_NvMData
  Type: Client-Server (asynchronous with callback)
  Provider: NvMManager (NvM_BSW)
  Consumer: DiagnosticManager, FlashManager, ECUStateManager
  Port Names:
    - NvM_ReadPort: read block request port
    - NvM_WritePort: write block request port
    - NvM_CallbackPort: job result callback port

5.4 Interface: ECU State Interface
  Name: If_EcuState
  Type: Sender-Receiver and Mode-Switch
  Provider: ECUStateManager (EcuM_BSW)
  Consumer: MotorControlSWC, CommunicationManager, FlashManager
  Port Names:
    - EcuM_StatePort: sender port (ECU current state)
    - EcuM_RequestRunPort: receiver port (RUN mode requests)
    - EcuM_ModePort: mode switch port (ECU lifecycle phases)

5.5 Interface: Motor Control Interface
  Name: If_MotorControl
  Type: Sender-Receiver
  Provider: MotorControlSWC (MotCtrl_SWC)
  Consumer: DiagnosticManager (monitoring), CAN stack (reporting)
  Port Names:
    - MotCtrl_TorqueSetpointPort: receiver port (target torque input)
    - MotCtrl_ActualTorquePort: sender port (actual torque feedback)
    - MotCtrl_FaultPort: sender port (motor fault status)

5.6 Interface: Flash Programming Interface
  Name: If_FlashProgramming
  Type: Client-Server
  Provider: FlashManager (Flash_SWC)
  Consumer: DiagnosticManager (UDS reprogramming)
  Port Names:
    - Flash_ProgramPort: programming trigger receiver port
    - Flash_StatusPort: programming status sender port

========================================================================
6. SIGNALS
========================================================================

6.1 Diagnostic Signals
  Signal: Diag_Request_Signal
    Direction: CAN RX to DiagnosticManager
    Type: UDS request PDU
    Length: Variable (max 4095 bytes, CAN TP segmented)
    Description: Raw UDS diagnostic request from external tester

  Signal: Diag_Response_Signal
    Direction: DiagnosticManager to CAN TX
    Type: UDS response PDU
    Length: Variable (max 4095 bytes, CAN TP segmented)
    Description: UDS diagnostic response from ECU

  Signal: Diag_SessionState
    Type: uint8
    Range: 0=DEFAULT, 1=EXTENDED, 2=PROGRAMMING
    Description: Current active diagnostic session state

  Signal: Diag_SecurityLevel
    Type: uint8
    Range: 0=LOCKED, 1=LEVEL1_UNLOCKED, 2=LEVEL2_UNLOCKED
    Description: Current security access level for diagnostic services

  Signal: Diag_FaultInhibit
    Type: boolean
    Description: Active fault inhibit signal from DiagnosticManager
    Consumer: MotorControlSWC (safety shutdown trigger)

6.2 CAN Communication Signals
  Signal: CAN_TX_PDU
    Direction: ECU to CAN bus
    Type: CAN frame (standard or extended ID)
    Length: 1-8 bytes (CAN 2.0) or up to 64 bytes (CAN FD)
    Description: CAN frame queued for transmission

  Signal: CAN_RX_PDU
    Direction: CAN bus to ECU
    Type: CAN frame
    Length: 1-8 bytes
    Description: Received CAN frame delivered to CanIf

  Signal: CAN_BusState
    Type: uint8
    Range: 0=ACTIVE, 1=BUS_OFF, 2=SLEEP, 3=STOPPED
    Description: Current CAN controller bus state

6.3 Flash and NvM Signals
  Signal: Flash_ProgrammingStatus
    Type: uint8
    Range: 0=IDLE, 1=IN_PROGRESS, 2=SUCCESS, 3=FAILED, 4=VERIFY_OK
    Description: Current flash programming operation status

  Signal: NvM_JobResult
    Type: uint8
    Range: NVM_REQ_OK, NVM_REQ_PENDING, NVM_REQ_NOT_OK, NVM_REQ_NV_INVALIDATED
    Description: Result of last NvM read/write operation

6.4 Motor Control Signals
  Signal: MotCtrl_TorqueSetpoint
    Direction: CAN RX to MotorControlSWC
    Type: sint16
    Unit: Nm x 10 (resolution 0.1 Nm)
    Range: -5000 to +5000 (physical: -500 to +500 Nm)
    Description: Target motor torque requested by vehicle controller

  Signal: MotCtrl_ActualTorque
    Direction: MotorControlSWC to CAN TX
    Type: sint16
    Unit: Nm x 10 (resolution 0.1 Nm)
    Description: Actual motor torque measured by current sensors

  Signal: MotCtrl_FaultActive
    Type: boolean
    Description: Motor fault active flag (triggers diagnostic fault)

6.5 ECU State Signals
  Signal: EcuM_CurrentState
    Type: uint8 (AUTOSAR EcuM_StateType enumeration)
    Values: STARTUP, APP_RUN, APP_POST_RUN, SLEEP, SHUTDOWN
    Description: Current ECU lifecycle state published by ECUStateManager

  Signal: EcuM_RunRequest
    Type: boolean
    Description: RUN mode request from application SWC to ECUStateManager

6.6 Communication Manager Signals
  Signal: ComM_ChannelMode
    Type: uint8
    Values: NO_COMMUNICATION, SILENT_COMMUNICATION, FULL_COMMUNICATION
    Description: Current CAN channel communication mode

========================================================================
7. DEPENDENCIES
========================================================================

7.1 Application Layer Component Dependencies
  DiagnosticManager -> CANDriver (via PduR and CanIf for CAN messaging)
  DiagnosticManager -> NvMManager (fault data and DID persistent storage)
  DiagnosticManager -> FlashManager (UDS reprogramming trigger)
  FlashManager -> NvMManager (programming status persistence)
  FlashManager -> CANDriver (implicitly via CanIf flash data transfer)
  MotorControlSWC -> DiagnosticManager (receives Diag_FaultInhibit signal)
  MotorControlSWC -> ECUStateManager (receives EcuM_CurrentState signal)

7.2 BSW Stack Dependencies
  DiagnosticManager -> DCM -> PduR -> CanIf -> CANDriver -> CAN Hardware
  NvMManager -> MemIf -> FEE -> FlashDriver -> Flash Hardware
  NvMManager -> MemIf -> EA -> EepromDriver -> EEPROM Hardware
  ECUStateManager -> BswM -> ComM -> CanSM -> CanNm -> CANDriver
  ECUStateManager -> Os (task scheduling and event notification)

7.3 Initialization Sequence (Boot Order)
  Phase 1 - Pre-OS (EcuM_AL_DriverInitZero):
    1.1 MCU initialization (clock, PLL, peripheral clocks)
    1.2 Port/DIO initialization
    1.3 Watchdog initialization

  Phase 2 - Pre-Scheduler (EcuM_AL_DriverInitOne):
    2.1 CANDriver initialization (Can_Init)
    2.2 CanIf initialization
    2.3 CommunicationManager initialization
    2.4 ECUStateManager initialization

  Phase 3 - Post-OS (Task_Init_BSW):
    3.1 PduR initialization
    3.2 NvMManager initialization and block reading
    3.3 DiagnosticManager initialization (DCM, DEM)
    3.4 FlashManager initialization

  Phase 4 - Application Init (Task_Init_App):
    4.1 MotorControlSWC initialization
    4.2 Motor calibration data loaded from NvMManager
    4.3 RTE started (Rte_Start)

7.4 Shutdown Sequence
  Application components release RUN mode (EcuM_ReleaseRUN)
  ECUStateManager transitions to APP_POST_RUN state
  NvMManager writes all modified blocks to NvM storage
  DiagnosticManager stores any pending DTC data
  CommunicationManager transitions to NO_COMMUNICATION
  CANDriver sends CanNm sleep indication
  ECUStateManager transitions to SHUTDOWN and halts CPU

========================================================================
8. FUNCTIONAL FLOWS
========================================================================

8.1 Diagnostic Request Flow (UDS Service 0x22 ReadDataByIdentifier)
  Step 1: External tester sends UDS ReadDataByIdentifier request (0x22)
          via CAN bus (CAN ID: 0x7DF broadcast or 0x700+ECU_ADDR physical)
  Step 2: CANDriver receives CAN frame interrupt, calls CanIf_RxIndication()
  Step 3: CanIf routes PDU to PduR based on CAN ID mapping
  Step 4: PduR routes PDU to DCM (DiagnosticManager) Rx buffer
          via TP layer (ISO 15765-2) for segmented messages
  Step 5: DiagnosticManager processes request in Dcm_MainFunction() (10ms)
          - Session check: Is DEFAULT or EXTENDED session active?
          - DID lookup: Is the requested DID 0xXXXX supported?
          - Permission check: Is security level sufficient?
  Step 6: DiagnosticManager reads DID data from NvMManager or application
  Step 7: DiagnosticManager constructs positive response PDU (0x62 + DID + data)
  Step 8: Response PDU sent via PduR -> CanIf -> CANDriver -> CAN bus
  Step 9: External tester receives response (typically within 50ms P2 timer)

8.2 Flash Reprogramming Flow (UDS Services 0x10, 0x27, 0x34, 0x36, 0x37)
  Step 1:  External tester requests Programming Session (UDS 0x10 0x02)
           DiagnosticManager validates and switches to PROGRAMMING_SESSION
  Step 2:  Tester requests Security Access seed (UDS 0x27 0x01)
           DiagnosticManager generates seed and sends response
  Step 3:  Tester sends calculated key (UDS 0x27 0x02)
           DiagnosticManager validates key, unlocks security level
  Step 4:  Tester sends Erase Memory request (UDS 0x31 0x01)
           DiagnosticManager notifies FlashManager to erase target sector
  Step 5:  FlashManager executes flash erase via Fls_Erase() MCAL call
           FlashManager updates NvM_ProgrammingStatus to IN_PROGRESS
  Step 6:  Tester sends RequestDownload (UDS 0x34) with memory address
           DiagnosticManager validates address and grants download permission
  Step 7:  Tester sends data blocks via TransferData (UDS 0x36)
           DiagnosticManager passes each block to FlashManager
           FlashManager writes each block via Fls_Write() MCAL call
  Step 8:  Tester sends RequestTransferExit (UDS 0x37)
           FlashManager verifies written data CRC
           FlashManager updates NvM_ProgrammingStatus to SUCCESS or FAILED
  Step 9:  DiagnosticManager sends positive response
           ECU performs software reset (EcuM_AL_Reset)
           New software image boots and initializes

8.3 Motor Torque Control Flow (Normal Operation)
  Step 1: Vehicle controller sends torque setpoint via HS-CAN
          CAN message ID 0x210, Signal MotCtrl_TorqueSetpoint
  Step 2: CANDriver receives frame, CanIf delivers to Com layer
          PduR routes to MotorControlSWC receiver port
  Step 3: MotorControlSWC_MainFunction() runs in Task_1ms
          Reads MotCtrl_TorqueSetpoint from RTE receiver port
  Step 4: Safety check: Is Diag_FaultInhibit signal active?
          If YES: Set PWM duty cycle to 0 (zero torque)
          If NO: Continue to control step
  Step 5: Read ECU state: Is EcuM_CurrentState == APP_RUN?
          If NO: Set PWM duty cycle to 0 (safe state)
          If YES: Apply PID control algorithm
  Step 6: PID controller calculates PWM duty cycle
          based on setpoint vs actual torque error
  Step 7: Pwm_SetDutyCycle() called to set inverter gate signals
  Step 8: ADC reads motor current feedback (every 1ms)
          Actual torque calculated from current measurements
  Step 9: MotCtrl_ActualTorque signal updated via RTE sender port
          Signal transmitted on CAN bus every 10ms for monitoring

8.4 ECU Wakeup Flow (CAN Wakeup)
  Step 1: CAN wakeup pattern detected on HS-CAN bus
  Step 2: CANDriver hardware wakeup interrupt fires
  Step 3: ECUStateManager notified of CAN wakeup source
  Step 4: ECUStateManager transitions from SLEEP to STARTUP
  Step 5: All BSW modules re-initialized in correct sequence
  Step 6: NvMManager reads back persistent data blocks
  Step 7: Application SWCs initialized and RTE started
  Step 8: CommunicationManager transitions to FULL_COMMUNICATION
  Step 9: DiagnosticManager ready for diagnostic requests

========================================================================
9. CONFIGURATION
========================================================================

9.1 CAN Configuration
  HS-CAN Controller:
    - Baud rate: 500 kbps
    - Hardware object TX buffers: 8
    - Hardware object RX buffers: 16
    - CAN ID type: Mixed (standard and extended)
    - Receive filter: Acceptance mask 0x7FF

  MS-CAN Controller:
    - Baud rate: 125 kbps
    - Hardware object TX buffers: 4
    - Hardware object RX buffers: 8

9.2 Diagnostic Configuration
  - Diagnostic protocol: ISO 14229-1 (UDS)
  - Transport layer: ISO 15765-2 (CAN TP)
  - Physical addressing CAN ID: 0x740 (request), 0x760 (response)
  - Functional addressing CAN ID: 0x7DF
  - P2 timer (response timing): 50ms
  - P2* timer (enhanced timing): 5000ms
  - Supported DIDs: 0xF101-0xF120 (PCU specific)
  - Diagnostic buffer size: 4096 bytes max

9.3 NvM Configuration
  NvM Block Layout:
    - Block NvM_DiagnosticDTC: Block ID 1, Size 256 bytes, CRC-32
    - Block NvM_CalibrationData: Block ID 2, Size 512 bytes, CRC-32
    - Block NvM_ProgrammingStatus: Block ID 3, Size 16 bytes, CRC-16
    - Block NvM_EcuConfig: Block ID 4, Size 128 bytes, CRC-32
    - Block NvM_FreezeFrame: Block ID 5, Size 64 bytes, CRC-16
  Total NvM size: 976 bytes used of 64 KB available

9.4 Flash Configuration
  - Application flash base address: 0x00080000
  - Application flash size: 3 MB (0x300000 bytes)
  - Flash sector size: 64 KB (0x10000 bytes)
  - Bootloader flash base: 0x00000000
  - Bootloader flash size: 1 MB (0x100000 bytes)
  - Flash write alignment: 8 bytes (double word)

9.5 AUTOSAR OS Configuration
  Tasks:
    - Task_1ms: Priority 10 (highest), MotorControlSWC
    - Task_5ms: Priority 8, ECUStateManager
    - Task_10ms: Priority 5, DiagnosticManager, CommunicationManager
    - Task_100ms: Priority 2, NvMManager, FlashManager
    - Task_Background: Priority 1 (lowest), housekeeping
  ISR:
    - ISR_CAN_Rx: Category 2, CAN receive interrupt (priority 15)
    - ISR_CAN_Tx: Category 2, CAN transmit confirmation (priority 12)
    - ISR_ADC: Category 2, ADC conversion complete (priority 14)

========================================================================
10. KNOWN LIMITATIONS AND FUTURE WORK
========================================================================

10.1 Current Limitations of This Version
  - Ethernet (DoIP) diagnostic transport not implemented
  - SOME_IP service discovery not included
  - SecOC (Secure Onboard Communication) for CAN message authentication
    is planned but not yet implemented in this version
  - Adaptive AUTOSAR elements are out of scope for this Classic release
  - OTA (Over-The-Air) update mechanism not implemented
  - UDS services 0x2F (InputOutputControlByIdentifier) not supported

10.2 Potential Improvements for Future Versions
  - Add DoIP transport layer for Ethernet-based diagnostics
  - Integrate SecOC module for CAN message MAC verification
  - Add SOME_IP/SD for service-oriented vehicle API exposure
  - Expand MotorControlSWC with field-weakening and MTPA algorithms
  - Implement UDS 0x2F for actuator control during diagnostics
  - Add OTA update capability via 4G/LTE telematics unit

10.3 Known Technical Debt
  - NvM_CalibrationData block does not yet have range validation
  - CommunicationManager sleep timeout is hardcoded at 2 seconds
  - MotorControlSWC PID gains are not runtime-adjustable via DID
  - DiagnosticManager P2 timer is fixed and not configurable via DID

========================================================================
END OF DOCUMENT
Project: PCU Demo ECU - AUTOSAR HLD AI Assistant Synthetic Data
Document: PCU-HLD-0001 Version 1.0
Status: SYNTHETIC DEMO DATA - For demonstration and evaluation purposes only.
This document does not represent any real product or confidential design.
========================================================================
"""


def create_synthetic_hld(output_dir: Path) -> Path:
    """
    Generate the synthetic AUTOSAR HLD as a PDF (or text fallback).
    
    The PDF is created using ReportLab with proper page structure so that
    PyMuPDF can extract real page numbers during ingestion.
    
    Returns:
        Path to the generated file (.pdf or .txt).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors

        pdf_path = output_dir / "AUTOSAR_HLD_Demo.pdf"

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=2.0 * cm,
            leftMargin=2.0 * cm,
            topMargin=2.0 * cm,
            bottomMargin=2.0 * cm,
        )
        styles = getSampleStyleSheet()

        # Define styles
        warning_style = ParagraphStyle(
            "Warning2",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.red,
            spaceAfter=4,
        )
        title_style = ParagraphStyle(
            "Title2",
            parent=styles["Title"],
            fontSize=14,
            spaceAfter=10,
            textColor=colors.darkblue,
        )
        h1_style = ParagraphStyle(
            "H1_2",
            parent=styles["Heading1"],
            fontSize=12,
            spaceAfter=6,
            spaceBefore=10,
            textColor=colors.darkblue,
        )
        h2_style = ParagraphStyle(
            "H2_2",
            parent=styles["Heading2"],
            fontSize=10,
            spaceAfter=4,
            spaceBefore=6,
            textColor=colors.navy,
        )
        body_style = ParagraphStyle(
            "Body2",
            parent=styles["Normal"],
            fontSize=8,
            spaceAfter=3,
            leading=12,
        )
        mono_style = ParagraphStyle(
            "Mono2",
            parent=styles["Code"],
            fontSize=7,
            spaceAfter=2,
            leading=10,
        )

        story = []

        for raw_line in SYNTHETIC_TEXT.split("\n"):
            line = raw_line.rstrip()

            if not line.strip():
                story.append(Spacer(1, 3))
                continue

            stripped = line.strip()

            # Skip separator lines
            if stripped.startswith("==="):
                story.append(Spacer(1, 4))
                continue

            # Warning line
            if stripped.startswith("SYNTHETIC DEMO"):
                story.append(Paragraph(stripped, warning_style))
                continue

            # Doc title line
            if stripped.startswith("AUTOSAR HIGH-LEVEL"):
                story.append(Spacer(1, 8))
                story.append(Paragraph(stripped, title_style))
                continue

            # END OF DOCUMENT lines
            if stripped.startswith("END OF DOCUMENT") or stripped.startswith("Project:") and "PCU Demo" in stripped:
                story.append(Paragraph(stripped, body_style))
                continue

            # Section heading: "1. INTRODUCTION" or "10. KNOWN LIMITATIONS"
            import re
            if re.match(r"^\d+\.\s+[A-Z]", stripped) and len(stripped) < 80:
                story.append(Paragraph(stripped, h1_style))
                continue

            # Sub-heading: "1.1 Purpose" or "4.1 DiagnosticManager"
            if re.match(r"^\d+\.\d+\s+", stripped) and len(stripped) < 100:
                story.append(Paragraph(stripped, h2_style))
                continue

            # Code/signal lines (indented with spaces, start with -)
            if line.startswith("  ") and stripped.startswith("-"):
                safe = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe, mono_style))
                continue

            # Regular body text
            safe_line = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Replace ASCII arrows
            safe_line = safe_line.replace("->", "---&gt;")
            story.append(Paragraph(safe_line, body_style))

        doc.build(story)
        return pdf_path

    except Exception as e:
        # Fallback: write as UTF-8 plain text
        txt_path = output_dir / "AUTOSAR_HLD_Demo.txt"
        txt_path.write_text(SYNTHETIC_TEXT, encoding="utf-8")
        return txt_path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from config.settings import DATA_INPUT_DIR
    path = create_synthetic_hld(DATA_INPUT_DIR)
    print(f"Created: {path} ({path.stat().st_size:,} bytes)")
