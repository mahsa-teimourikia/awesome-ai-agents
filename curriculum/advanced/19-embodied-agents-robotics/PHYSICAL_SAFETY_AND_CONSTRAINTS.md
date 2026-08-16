# Deep Dive: Physical Safety and Constraints

When an agent interacts with a web API, a hallucination might result in a `400 Bad Request`. When an embodied agent controls a robotic arm, a hallucination can cause a 50kg steel arm to swing through a glass window. 

Robotic systems must separate **non-deterministic intelligence** from **deterministic safety**.

## Semantic Goals vs. Low-Level Control

You must never allow an LLM to directly output motor voltages, PWM signals, or raw joint velocities. LLMs are non-deterministic and have high latency (e.g., 2-5 seconds). Controlling a motor requires deterministic calculations running at 1000Hz.

Instead, the VLA (Vision-Language-Action) model outputs a **Semantic Goal** (e.g., "Move the end-effector to Cartesian coordinates `X: 0.5, Y: 0.2, Z: 0.1`").

A deterministic Low-Level Controller (usually using Inverse Kinematics and PID loops) calculates the exact motor voltages required to achieve that goal smoothly.

## The Safety Supervisor

Between the LLM and the Low-Level Controller sits the **Safety Supervisor**. This is a hard-coded, deterministic program that cannot be overridden by the LLM. It acts as the ultimate authority.

### 1. Geofencing
The Supervisor maintains a 3D bounding box of the allowed workspace. If the LLM requests a coordinate outside that box (e.g., towards a human operator), the Supervisor intercepts the command, halts the robot, and returns a severe error to the LLM.

### 2. Force and Torque Limits
If an LLM instructs a robot to "Place the cup on the table", but miscalculates the depth, the robot will drive the cup *through* the table. 
The Safety Supervisor constantly monitors the physical torque sensors on the robot joints. If the force exceeds a safe threshold (e.g., > 10 Newtons), the Supervisor instantly triggers a hard stop.

### 3. The Hardware Kill Switch (E-Stop)
Regardless of the software stack, every embodied agent must be physically wired to a giant red Emergency Stop button. If a human hits the E-Stop, power to the motors is cut at the hardware level, bypassing all software logic.
