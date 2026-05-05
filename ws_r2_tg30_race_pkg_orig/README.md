# ROSMASTER R2 TG30 Race Workspace

This zip is a **clean starting point**.
It keeps your old workspaces safe and separate.

This updated version adds four things you asked for:

1. **Real RViz display files**
2. **A joystick deadman switch**
3. **A `/cmd_vel` to Ackermann bridge**
4. **Safer FTG starting numbers for sidewalk driving**

---

## What this workspace does

This workspace helps your ROSMASTER R2 do four big jobs:

- **Map** your driveway or sidewalk
- **Localize** on a saved map with AMCL
- **Follow a waypoint path** with pure pursuit
- **Avoid surprise obstacles** with follow-the-gap (FTG)

The motion flow is now:

```text
Pure Pursuit      -> /cmd_vel_auto_raw
Deadman Gate      -> /cmd_vel_auto
FTG + Blend Node  -> /cmd_vel_safety
twist_mux         -> /cmd_vel
Ackermann Bridge  -> /ackermann_cmd
```

So the robot thinks in normal ROS `Twist`, but the final bridge converts that into an Ackermann message for the real car.

---

## Important idea in simple words

Think of the stack like this:

### Part 1: The LiDAR looks ahead
The TG30 scans the world.

### Part 2: The scan gets cleaned
Because the LiDAR is tilted down, some rays can hit the ground.
So we filter the scan and rebuild a cleaner obstacle scan.

### Part 3: Pure pursuit follows the path
Pure pursuit tries to stay on the saved race line.

### Part 4: FTG helps when something blocks the way
If something is in front of the car, FTG points the car toward a safer opening.

### Part 5: The deadman button must be held
If you do not hold the deadman button, auto drive is blocked.
That makes testing much safer.

### Part 6: The final command gets converted for the car
`/cmd_vel` gets turned into `/ackermann_cmd`.
That is the message many Ackermann car controllers want.

---

## Big safety rules

Please do these the first time:

- Put the car on a stand first.
- Keep one hand ready to stop power.
- Start with very low speed.
- Test steering direction before floor driving.
- Test deadman before auto driving.
- Do not test near traffic, stairs, pets, or people.

---

## What changed from the first zip

### 1) RViz displays were added
You now have:

- `rviz/mapping.rviz`
- `rviz/localization.rviz`
- `rviz/racing.rviz`

And quick launch files:

- `roslaunch r2_tg30_race view_mapping.launch`
- `roslaunch r2_tg30_race view_localization.launch`
- `roslaunch r2_tg30_race view_racing.launch`

### 2) Joystick deadman was added
New nodes:

- `joy_deadman.py`
- `cmdvel_gate.py`

The deadman node watches `/joy` and publishes `/auto_enable`.
The gate only lets autonomy move the car while the button is held.

### 3) `/cmd_vel` now gets converted to Ackermann output
New node:

- `twist_to_ackermann.py`

Default output topic:

- `/ackermann_cmd`

### 4) FTG was tuned to a safer sidewalk starting point
The starting numbers are more conservative for a small outdoor car:

- FTG danger distance: **0.85 m**
- FTG stop distance: **0.35 m**
- Steering blend starts getting strong by about **1.2 m**

That means the car starts caring about obstacles early enough to be useful, but not so early that it keeps fighting the sidewalk edges all the time.

---

## Folder layout

```text
ws_r2_tg30_race_pkg/
├── README.md
└── src/
    ├── ydlidar_ros_driver/
    │   └── README_EXTERNAL_DRIVER.md
    └── r2_tg30_race/
        ├── launch/
        ├── config/
        ├── scripts/
        ├── rviz/
        ├── urdf/
        ├── maps/
        ├── bags/
        └── waypoints/
```

---

## Assumptions used

These are the defaults I used because your exact motor-controller interface file was not inside this workspace yet:

- ROS1 **Noetic**
- Ubuntu **20.04**
- Main scan topic: **`/scan`**
- Base frame: **`base_link`**
- Laser frame: **`lidar_link`**
- Odom topic: **`/odom`**
- Deadman button default: **button index 5**
- Final Ackermann topic: **`/ackermann_cmd`**
- Wheelbase default: **0.26 m**
- Max steering angle default: **0.45 rad**

If your real controller wants a different topic name, change:

```text
src/r2_tg30_race/config/ackermann_bridge.yaml
```

If your joystick button mapping is different, change:

```text
src/r2_tg30_race/config/joystick_deadman.yaml
```

---

## Install packages

```bash
sudo apt update

sudo apt install -y   ros-noetic-desktop-full   python3-catkin-tools   ros-noetic-ackermann-msgs   ros-noetic-joy   ros-noetic-laser-filters   ros-noetic-pointcloud-to-laserscan   ros-noetic-slam-gmapping   ros-noetic-amcl   ros-noetic-map-server   ros-noetic-octomap-server   ros-noetic-laser-geometry   ros-noetic-pcl-ros   ros-noetic-tf2-ros   ros-noetic-tf   ros-noetic-twist-mux   ros-noetic-rviz
```

---

## Keep this workspace separate from old ones

This workspace does **not** touch your `.bashrc`.
Use it only in the terminals where you want it.

```bash
cd ~/ws_r2_tg30_race_pkg
catkin_make
source devel/setup.bash
```

---

## First test order on the real car

### Terminal 1
```bash
roscore
```

### Terminal 2
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=false
```

Use `start_driver:=true` only if the real `ydlidar_ros_driver` package is inside this workspace.

### Terminal 3
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```

### Terminal 4
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_mapping.launch
```

Check these topics:

```bash
rostopic hz /scan
rostopic hz /scan_obstacles
```

---

## How to map

### Start mapping
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race mapping_gmapping.launch
```

### Open mapping RViz
```bash
roslaunch r2_tg30_race view_mapping.launch
```

Drive slowly and make one clean loop.

### Save the map
```bash
rosrun map_server map_saver -f ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course
```

---

## How to localize

### Start AMCL
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race localization_amcl.launch   map_file:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course.yaml
```

### Open localization RViz
```bash
roslaunch r2_tg30_race view_localization.launch
```

In RViz use **2D Pose Estimate** one time.
Then make sure the robot icon and scan line up with the map.

---

## How to build or load the race path

If you already have a waypoint YAML, the racing stack can load it.
The default file is:

```text
src/r2_tg30_race/waypoints/waypoints.yaml
```

If you need to build waypoints from odom or a bag, use the helper scripts already in the package:

- `waypoint_extractor.py`
- `waypoint_map_builder.py`

---

## How to run racing mode on the real car

### Start localization first
Keep AMCL running.

### Start racing stack
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race racing_stack.launch
```

### Open racing RViz
```bash
roslaunch r2_tg30_race view_racing.launch
```

### What to check before floor driving

```bash
rostopic echo /auto_enable
rostopic echo /cmd_vel_auto_raw
rostopic echo /cmd_vel_auto
rostopic echo /cmd_vel_safety
rostopic echo /cmd_vel
rostopic echo /ackermann_cmd
```

#### What you should see

- `/auto_enable` becomes **true** only while you hold the deadman button
- `/cmd_vel_auto_raw` is pure pursuit
- `/cmd_vel_auto` is gated pure pursuit
- `/cmd_vel_safety` is the PP+FTG blended safe command
- `/cmd_vel` is the final mux output
- `/ackermann_cmd` is the message for the Ackermann controller

---

## How the deadman works

The deadman is there so autonomy cannot keep driving if you let go.

Default file:

```text
src/r2_tg30_race/config/joystick_deadman.yaml
```

Default value:

```yaml
deadman_button_index: 5
```

If your controller uses a different button number, check it with:

```bash
rostopic echo /joy
```

Then change the index.
Common choices are **5**, **7**, or sometimes **9** depending on the joystick and driver.

---

## How the Ackermann bridge works

Your path and obstacle code still uses normal `Twist` messages because that is simple and common in ROS.
Then this node converts them:

```text
/cmd_vel -> /ackermann_cmd
```

Default file:

```text
src/r2_tg30_race/config/ackermann_bridge.yaml
```

Important settings:

```yaml
out_topic: /ackermann_cmd
wheelbase: 0.26
max_steering_angle: 0.45
steering_sign: 1.0
```

### If steering goes the wrong way
Change:

```yaml
steering_sign: -1.0
```

### If your controller wants a different topic
Change:

```yaml
out_topic: /your_real_ackermann_topic
```

---

## FTG numbers for sidewalk driving

These are starting numbers, not magic numbers.
They are meant to be a safer first guess.

### Current starting values

```yaml
danger_distance: 0.85
stop_distance: 0.35
blend_distance: 1.20
front_angle_deg: 85.0
```

### What they mean

- **danger_distance** = FTG starts caring a lot
- **stop_distance** = too close, stop and turn away
- **blend_distance** = start mixing PP and FTG
- **front_angle_deg** = how wide the car looks in front

### Easy tuning rule

If the car waits too long before reacting:
- raise `danger_distance` by **0.05 to 0.10 m**

If the car keeps fighting sidewalk edges too much:
- lower `danger_distance` by **0.05 m**
- or make `front_angle_deg` a little smaller

If the car steers around obstacles too late:
- raise `blend_distance`

If it panics too often:
- lower `blend_distance`

---

## About teleop with twist_mux

This package now includes a real `twist_mux` setup.
That means you can add your own teleop node later and publish to:

```text
/cmd_vel_teleop
```

Then the mux can choose between:

- `/cmd_vel_safety`
- `/cmd_vel_teleop`
- `/cmd_vel_auto`

The priority file is here:

```text
src/r2_tg30_race/config/twist_mux.yaml
```

---

## Simple race-day order

### 1. Bring up LiDAR
```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=false
```

### 2. Clean scan
```bash
roslaunch r2_tg30_race scan_cleanup.launch
```

### 3. Start localization
```bash
roslaunch r2_tg30_race localization_amcl.launch   map_file:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course.yaml
```

### 4. Start race stack
```bash
roslaunch r2_tg30_race racing_stack.launch
```

### 5. Open RViz
```bash
roslaunch r2_tg30_race view_racing.launch
```

### 6. Hold deadman and test on the stand first
Watch `/ackermann_cmd` before testing on the ground.

---

## Most important files to edit later

### Deadman button
```text
src/r2_tg30_race/config/joystick_deadman.yaml
```

### Ackermann output topic and steering sign
```text
src/r2_tg30_race/config/ackermann_bridge.yaml
```

### FTG starting numbers
```text
src/r2_tg30_race/config/follow_the_gap.yaml
src/r2_tg30_race/config/steering_modifier.yaml
```

### Mux priorities
```text
src/r2_tg30_race/config/twist_mux.yaml
```

---

## Honest note

Your two uploaded reference packages clearly showed the older **deadman + gate + mux** pattern, so I copied that idea into this clean workspace.
The only thing that still needs your final exact detail is the **real Ackermann motor-controller topic name** if your driver does not use `/ackermann_cmd`.

Everything else is now in the zip as a clean base you can keep building from.
