Here is the CXR2.0 firmware AI summary that Mike Baluch generated.  I recall now that this was heavily focused on the event stack architecture of the firmware, and perhaps not a general summary.  If you want a more general summary, I can ask him to generate that:
 
Here is a description of each event that gets added to the event stack, along with the logic for how events are processed:
Event Stack Overview
The event stack is a simple LIFO (last-in, first-out) buffer for system events.
Events are pushed onto the stack using EventStack_push(event) and popped using EventStack_pop().
The main loop pops events and passes them to the state machine for processing.
Typical Events Added to the Stack
1. EVENT_MOTOR_ON
Added when: The motor-on signal is detected (e.g., user activates the device).
Logic: If the system is in the idle state and the motor switch is high, this event is pushed.
Processing: The state machine transitions from idle to motor running, starting the motor and related actions.
2. EVENT_BAG_INSERTED
Added when: The bag inserted switch is triggered (e.g., a consumable is loaded).
Logic: Detected via input pin change; event is pushed when the bag is inserted.
Processing: The state machine transitions to the bag inserted state, updating flags and possibly starting a timer.
3. EVENT_EOS_CLOSED
Added when: The end-of-stroke (EOS) switch is closed.
Logic: Detected via input pin; event is pushed when EOS is closed.
Processing: The state machine may transition to a state indicating a completed action (e.g., dispensing done).
4. EVENT_MOTOR_OVERLOAD
Added when: Motor overload is detected (e.g., current exceeds threshold).
Logic: Overload flag is set; event is pushed to indicate a fault.
Processing: The state machine transitions to an error state, disables the motor, and signals an error.
5. EVENT_WDT
Added when: Watchdog timer interrupt occurs.
Logic: WDT flag is set; event is pushed to handle timeout or reset.
Processing: The state machine may reset the system or perform recovery actions.
Event Processing Logic
Main Loop:
Continuously pops events from the stack.
If an event is present (EventStack_pop() returns a value other than -1), it is passed to StateMachine_stateEval(event).
State Machine:
Evaluates the current state and the event.
Uses a state matrix to determine the next state and the action to perform.
Executes the corresponding action (e.g., start motor, signal error, update flags).
Event Generation:
Events are generated in response to hardware interrupts, input pin changes, or internal conditions (e.g., timers, overloads).
The function stackEvents() checks system flags and input pins, and pushes relevant events onto the stack.
Example Event Flow
User inserts a bag → EVENT_BAG_INSERTED is pushed.
Main loop pops the event → State machine transitions to "bag inserted" state.
Motor is started → EVENT_MOTOR_ON is pushed.
Motor overload detected → EVENT_MOTOR_OVERLOAD is pushed.
State machine transitions to error state and disables motor.
 
 
When a clear key (reset key) is inserted into the spout, the system performs a special reset operation:
Detection: The system reads the ekey (electronic key) data using the RFID transceiver. It checks if the inserted key is a reset key by comparing its identifier to a predefined reset code (often BAG_ID_RESET).
Reset Logic:
If the key is identified as a reset key, the system sets a flag (sysFlags.usingResetKey = 1).
The distributor code in EEPROM is set to 0xFF, allowing the dispenser to be imprinted again (i.e., ready for a new bag or distributor).
The system may also reset usage counters and other statistics, such as sysData.imprintCounter = 0.
State Machine: The state machine transitions to a state indicating the reset key is installed. This may prevent normal dispensing until a valid bag key is inserted.
Reporting: The system updates its status so that SmartLink or other communication protocols can report that a reset key is present.
Summary:
Inserting a clear key into the spout resets the dispenser’s usage statistics and allows it to be re-imprinted for a new bag or distributor. Normal dispensing is disabled until a valid consumable key is inserted.
If you want the exact code flow or more details on the EEPROM/statistics reset, let me know!
 
This is nuts.
 
The EEPROM reset logic is triggered when both of the following conditions are met:
Input Voltage > 6.8V:
The system detects that the battery/input voltage is above the threshold (BATT_RESET_STATS_VOLTAGE, typically 6.8V).
Reset Key Inserted:
The system reads the ekey and verifies that a reset key (clear key) is present in the spout.
When these conditions are satisfied, the function l_checkIdReset() executes the EEPROM reset logic, which resets distributor codes, usage counters, and other statistics in EEPROM, preparing the dispenser for a new cycle.
