# ROSMASTER R2 TG30 Race Stack README

## Beginner guide for the real car

This guide is written in simple words.
It tells you:

- what each part does
- what to turn on
- what to turn off
- which launch file to use
- what order to start things in
- how to test safely on the real car

This README matches the package in your zip:

- workspace: `ws_r2_tg30_race_pkg`
- main package: `r2_tg30_race`

---

# 1. What this package is for

This package helps your ROSMASTER R2 do four main jobs:

1. **See the world with the TG30 LiDAR**
2. **Make a map** of your driveway or sidewalk
3. **Find itself on the map** later
4. **Drive a saved path** using pure pursuit while follow-the-gap (FTG) helps avoid obstacles

It is set up for a **tilted TG30 LiDAR**.
That matters because the LiDAR is looking slightly down, so some beams can hit the ground.
Because of that, the package cleans the scan before using it for mapping and localization.

---

# 2. Big picture in easy words

Think of the system like this:

## Step A: the LiDAR scans the world
The TG30 publishes a laser scan on:

- `/scan`

## Step B: the scan gets cleaned
The package filters the raw scan and turns it into a cleaner obstacle scan:

- `/scan_filtered`
- `/scan_cloud`
- `/scan_obstacles`

`/scan_obstacles` is the main scan used for mapping, localization, and obstacle avoidance.

## Step C: pure pursuit tries to follow the race path
Pure pursuit reads:

- `/race_path`
- `/odom`

Then it publishes:

- `/cmd_vel_auto_raw`

## Step D: the deadman switch decides if auto is allowed
The joystick deadman node reads:

- `/joy`

and publishes:

- `/auto_enable`

If the button is not held, the robot should not drive in auto.

## Step E: FTG watches for danger ahead
FTG reads:

- `/scan_obstacles`

and publishes:

- `/cmd_vel_ftg_raw`

## Step F: the steering modifier blends path following and safety
The steering modifier mixes pure pursuit and FTG and publishes:

- `/cmd_vel_safety`

## Step G: twist_mux chooses the winning command
The mux chooses between:

- `/cmd_vel_safety`  ← highest priority
- `/cmd_vel_teleop`
- `/cmd_vel_auto`

Then it outputs:

- `/cmd_vel`

## Step H: the Ackermann bridge converts the final command
The bridge reads:

- `/cmd_vel`

and converts it into:

- `/ackermann_cmd`

That output is what your real Ackermann motor/steering interface will usually use.

---

# 3. Main topics you should know

## Sensor topics
- `/scan` = raw LiDAR scan
- `/scan_filtered` = cleaned scan
- `/scan_cloud` = point cloud made from scan
- `/scan_obstacles` = rebuilt obstacle-only scan

## Navigation topics
- `/odom` = robot motion estimate
- `/race_path` = path to follow
- `/waypoint_path` = path while recording waypoints

## Command topics
- `/cmd_vel_auto_raw` = pure pursuit output before deadman gate
- `/cmd_vel_auto` = pure pursuit after deadman gate
- `/cmd_vel_ftg_raw` = FTG output
- `/cmd_vel_safety` = blended safe command
- `/cmd_vel` = mux final twist command
- `/ackermann_cmd` = final Ackermann command for the real car

## Safety topics
- `/joy` = joystick input
- `/auto_enable` = true only while deadman button is held
- `/bag_record_cmd` = start/stop bag recording with true/false

---

# 4. Main launch files

These are the launch files you will use most.

## LiDAR bringup
```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=false
```
Use this when the TG30 driver is already being started some other way.

If the real `ydlidar_ros_driver` package is inside the workspace and you want this package to start it, use:

```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=true
```

## Scan cleanup
```bash
roslaunch r2_tg30_race scan_cleanup.launch
```
This turns the tilted scan into a more useful obstacle scan.

## Mapping
```bash
roslaunch r2_tg30_race mapping_gmapping.launch start_driver:=false
```

## Localization
```bash
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false
```

## Racing stack
```bash
roslaunch r2_tg30_race racing_stack.launch start_driver:=false
```

## RViz windows
```bash
roslaunch r2_tg30_race view_mapping.launch
roslaunch r2_tg30_race view_localization.launch
roslaunch r2_tg30_race view_racing.launch
```

---

# 5. What should be ON and OFF

This part is important.
A lot of problems happen because too many things are running at once.

## Always ON
These are usually on for all modes:

- `roscore`
- TG30 LiDAR driver or `tg30_bringup.launch`
- scan cleanup pipeline
- your odometry source publishing `/odom`

## ON only when mapping
Turn these ON only during map making:

- `mapping_gmapping.launch`
- optional RViz mapping window

Turn these OFF during mapping:

- `localization_amcl.launch`
- `racing_stack.launch`

## ON only when localizing
Turn these ON only during localization:

- `localization_amcl.launch`
- optional RViz localization window

Turn these OFF during localization:

- `mapping_gmapping.launch`
- `racing_stack.launch` if you are only checking localization

## ON when racing
Turn these ON when you want the robot to drive a path:

- `localization_amcl.launch` or another good pose source
- `racing_stack.launch`
- joystick driver if you are using the deadman switch
- optional RViz racing window

Turn these OFF when racing:

- `mapping_gmapping.launch`

## Big rule
Do **not** run **gmapping and AMCL at the same time** for normal use.
One is making a map.
The other is using a map.
Running both together usually causes confusion.

---

# 6. One-time setup

## Step 1: install ROS packages
```bash
sudo apt update
sudo apt install -y \
  ros-noetic-desktop-full \
  python3-catkin-tools \
  ros-noetic-ackermann-msgs \
  ros-noetic-joy \
  ros-noetic-laser-filters \
  ros-noetic-pointcloud-to-laserscan \
  ros-noetic-slam-gmapping \
  ros-noetic-amcl \
  ros-noetic-map-server \
  ros-noetic-octomap-server \
  ros-noetic-laser-geometry \
  ros-noetic-pcl-ros \
  ros-noetic-tf2-ros \
  ros-noetic-tf \
  ros-noetic-twist-mux \
  ros-noetic-rviz
```

## Step 2: build the workspace
```bash
cd ~/ws_r2_tg30_race_pkg
catkin_make
```

## Step 3: source the workspace in every terminal you use for this package
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
```

Important:
This workspace is meant to stay separate.
It does **not** need to edit your `.bashrc`.
Just source it in each terminal when you want to use it.

---

# 7. Check the LiDAR geometry

The package assumes this static TF:

- base frame: `base_link`
- lidar frame: `lidar_link`
- x = `0.20`
- y = `0.00`
- z = `0.1143`
- pitch = `-5 degrees`

That is already built into:

```bash
roslaunch r2_tg30_race tg30_bringup.launch
```

If your LiDAR is mounted differently, edit the launch file:

- `src/r2_tg30_race/launch/tg30_bringup.launch`

---

# 8. Real car safety checklist

Do these before the first floor test.

## First bench test
- Put the car on a stand so the wheels are off the ground.
- Make sure steering can move freely.
- Make sure the wheels do not hit wires.
- Keep a hand near the power switch.
- Keep speed low.

## First floor test
- Use a big open space.
- Keep people and pets away.
- Stay away from streets and stairs.
- Start very slow.
- Test the deadman button before trying auto.

## Stop rule
If anything looks wrong:
- let go of the deadman button
- or stop the launch file with `Ctrl+C`
- or cut car power

---

# 9. How to bring the system up for the first time

This is the safest first test order.

## Terminal 1: start ROS master
```bash
roscore
```

## Terminal 2: source the workspace
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
```

## Terminal 2: start the LiDAR TF and optional driver
If your TG30 driver is started somewhere else already:

```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=false
```

If you want this launch file to start the driver:

```bash
roslaunch r2_tg30_race tg30_bringup.launch start_driver:=true
```

## Terminal 3: start scan cleanup
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```

## Terminal 4: open RViz for checking the scan
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_mapping.launch
```

## Terminal 5: check the important topics
```bash
rostopic hz /scan
rostopic hz /scan_obstacles
rostopic echo -n 1 /scan_obstacles
```

What you want:
- `/scan` should be alive
- `/scan_obstacles` should be alive
- RViz should show a forward obstacle scan that makes sense

---

# 10. How to make a map

Use this mode when you want to drive around and create the map.

## Turn ON
- `roscore`
- LiDAR bringup
- scan cleanup
- gmapping
- RViz mapping view

## Turn OFF
- AMCL localization
- racing stack

## Terminal order

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
roslaunch r2_tg30_race mapping_gmapping.launch start_driver:=false
```

### Terminal 5
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_mapping.launch
```

## What to do next
- Slowly drive the car around the driveway and sidewalk.
- Try to overlap the path a little so the map closes nicely.
- Move slowly enough that the scan and odom can keep up.
- Watch RViz and see if walls, grass edges, and curb lines look stable.

## Save the map when finished
Open a new terminal:

```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
rosrun map_server map_saver -f ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course
```

That should create:
- `driveway_course.pgm`
- `driveway_course.yaml`

---

# 11. How to localize on a saved map

Use this mode after you already have a map.

## Turn ON
- `roscore`
- LiDAR bringup
- scan cleanup
- map server
- AMCL
- RViz localization view

## Turn OFF
- gmapping
- racing stack if you are only testing localization

## Terminal order

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
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false map_file:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course.yaml
```

### Terminal 5
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_localization.launch
```

## What to look for in RViz
- the map should stay still
- the robot pose should settle into the right place
- the laser scan should line up with map edges

If the pose is wrong at startup, use RViz 2D Pose Estimate and click the robot's starting spot.

---

# 12. How to record waypoints

This package has two waypoint tools:

1. **automatic sampling from `/odom`**
2. **manual marking with `/waypoint_mark`**

The waypoint extractor writes to:

- `~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml`

## Start the waypoint extractor
Open a new terminal:

```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
rosrun r2_tg30_race waypoint_extractor.py _sample_distance:=0.40 _frame_id:=map
```

What this means:
- every time the robot moves about 0.40 m, a waypoint is added
- the file is saved as it runs

## To add a manual waypoint mark
Open another terminal and run:

```bash
rostopic pub -1 /waypoint_mark std_msgs/Empty "{}"
```

That tells the waypoint extractor:
- “save a point here right now”

## To see the path in RViz
You can display:
- `/waypoint_path`

---

# 13. How to turn the waypoint file into the race path

The racing stack uses a path topic called:

- `/race_path`

That path is published by:

- `waypoint_map_builder.py`

The racing launch file already starts it for you.

If you want to run it by itself:

```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
rosrun r2_tg30_race waypoint_map_builder.py _yaml_file:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml _path_topic:=/race_path
```

---

# 14. How to record a rosbag

The package includes:

- `bag_control_recorder.py`

It listens to:

- `/bag_record_cmd`

## Start the recorder node
Open a new terminal:

```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
rosrun r2_tg30_race bag_control_recorder.py
```

## Start recording
```bash
rostopic pub -1 /bag_record_cmd std_msgs/Bool "data: true"
```

## Stop recording
```bash
rostopic pub -1 /bag_record_cmd std_msgs/Bool "data: false"
```

The bag files are saved in:

```text
~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags/
```

The default recorded topics are:
- `/scan`
- `/scan_filtered`
- `/scan_obstacles`
- `/tf`
- `/odom`
- `/cmd_vel`
- `/joy`
- `/imu/data`

---

# 15. How to race the path on the real car

Use this when you want pure pursuit plus FTG obstacle avoidance.

## Turn ON
- `roscore`
- LiDAR bringup
- scan cleanup
- localization on a saved map or another good pose source
- joystick driver
- racing stack
- RViz racing view if you want to watch it

## Turn OFF
- gmapping mapping

## Important note
The racing stack needs a good pose source.
The package expects `/odom` for pure pursuit.
For best real-world driving, also have AMCL or another pose source stable in the system.

## Terminal order for a real run

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

### Terminal 3
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```

### Terminal 4
Start localization:
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false map_file:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course.yaml
```

### Terminal 5
Start the joystick node:
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
rosrun joy joy_node
```

### Terminal 6
Start racing:
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race racing_stack.launch start_driver:=false waypoint_yaml:=~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml use_ackermann_bridge:=true
```

### Terminal 7
Optional RViz:
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_racing.launch
```

---

# 16. How the joystick deadman works

This is one of the most important safety parts.

## Default deadman button
The package uses:

- button index `5`

from:

- `config/joystick_deadman.yaml`

That means the robot only allows auto motion when button 5 is held.

## How to test it
Open a terminal:

```bash
rostopic echo /auto_enable
```

Then press and hold the deadman button.

You should see:

- `data: true` while held
- `data: false` when released

If it stays false:
- make sure `joy_node` is running
- check `rostopic echo /joy`
- verify the button number is right for your controller

## If your joystick uses a different button
Edit this file:

```text
src/r2_tg30_race/config/joystick_deadman.yaml
```

Change:

```yaml
deadman_button_index: 5
```

Then relaunch the racing stack.

---

# 17. How the mux works

The mux is like a referee.
It decides which command gets control.

The priorities are:

1. **safety** = `/cmd_vel_safety` = priority 100
2. **teleop** = `/cmd_vel_teleop` = priority 90
3. **auto** = `/cmd_vel_auto` = priority 50

So if safety is talking, it wins.
That is good.

If teleop is talking and safety is quiet, teleop wins.
If only auto is talking, auto wins.

This is controlled by:

```text
src/r2_tg30_race/config/twist_mux.yaml
```

---

# 18. How pure pursuit and FTG work together

## Pure pursuit job
Pure pursuit tries to follow the saved path smoothly.

It publishes:
- `/cmd_vel_auto_raw`

## Deadman gate job
The gate only lets pure pursuit through if the deadman is on.

It changes:
- `/cmd_vel_auto_raw` into `/cmd_vel_auto`

## FTG job
FTG watches for open space and danger in front.

It publishes:
- `/cmd_vel_ftg_raw`

## Steering modifier job
The steering modifier blends them.

- if the way is clear, it mostly follows pure pursuit
- if something is close, it listens more to FTG
- if something is too close, it can stop forward motion and steer toward open space

The steering modifier publishes:
- `/cmd_vel_safety`

That is the command with the highest mux priority.

---

# 19. FTG starting values for sidewalk driving

These are the current starting numbers:

- `danger_distance: 0.85`
- `stop_distance: 0.35`
- `blend_distance: 1.20`

What they mean:

## danger distance
If something is closer than about 0.85 m, the system starts caring a lot more about FTG.

## stop distance
If something is closer than about 0.35 m in front, the robot stops driving forward and focuses on turning away.

## blend distance
If things are farther away than about 1.20 m, the robot mostly trusts pure pursuit.

## If the robot reacts too early
Lower these a little:
- `danger_distance`
- `blend_distance`

## If the robot reacts too late
Raise these a little:
- `danger_distance`
- maybe `stop_distance`

Edit this file:

```text
src/r2_tg30_race/config/steering_modifier.yaml
```

And also check:

```text
src/r2_tg30_race/config/follow_the_gap.yaml
```

Change only a little at a time.
For example change 0.85 to 0.75, not all the way to 0.30.

---

# 20. How to test the Ackermann bridge

The bridge converts `/cmd_vel` into `/ackermann_cmd`.

## Check that it is publishing
```bash
rostopic echo /ackermann_cmd
```

You should see:
- speed
- steering angle

## If steering is backwards
Edit:

```text
src/r2_tg30_race/config/ackermann_bridge.yaml
```

Change:

```yaml
steering_sign: 1.0
```

to:

```yaml
steering_sign: -1.0
```

Then relaunch the racing stack.

## If steering is too strong or too weak
Also change:

```yaml
wheelbase: 0.26
max_steering_angle: 0.45
```

---

# 21. How to turn things OFF in the right order

This is the safest stop order.

## If racing
1. let go of deadman button
2. stop the racing stack terminal with `Ctrl+C`
3. stop localization with `Ctrl+C`
4. stop scan cleanup with `Ctrl+C`
5. stop TG30 bringup with `Ctrl+C`
6. stop `roscore` last

## If mapping
1. stop moving the car
2. save the map
3. stop gmapping with `Ctrl+C`
4. stop scan cleanup with `Ctrl+C`
5. stop TG30 bringup with `Ctrl+C`
6. stop `roscore` last

---

# 22. Replay a bag later

You can replay a rosbag and let ROS time come from the bag.

## Terminal 1
```bash
roscore
```

## Terminal 2
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
rosparam set use_sim_time true
```

## Terminal 3
Play the bag:
```bash
rosbag play --clock ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags/your_bag_name.bag
```

Then in other terminals you can run scan cleanup, RViz, waypoint extraction, or other nodes against the bag data.

---

# 23. Easy troubleshooting checklist

## Problem: no `/scan`
Check:
- is the TG30 plugged in?
- is the right serial port used?
- is the real driver running?
- if using this package to start the driver, did you use `start_driver:=true`?

## Problem: `/scan` exists but `/scan_obstacles` does not
Check:
- did you launch `scan_cleanup.launch`?
- does RViz show TF from `base_link` to `lidar_link`?
- is `scan_to_cloud.py` running?
- is `pointcloud_to_laserscan_node` running?

## Problem: deadman does not enable auto
Check:
- is `rosrun joy joy_node` running?
- does `/joy` exist?
- does `/auto_enable` change to true when button 5 is held?
- is the button index correct for your joystick?

## Problem: `/cmd_vel` exists but the real car does not move
Check:
- does your controller listen to `/ackermann_cmd`?
- is the controller bridge from `/ackermann_cmd` to hardware running?
- is steering sign backwards?
- is your motor controller interface expecting a different message type?

## Problem: map looks messy
Check:
- are you moving too fast?
- is `/odom` stable?
- is the LiDAR mount angle correct?
- are curb and grass edges being seen in a repeatable way?

## Problem: racing feels nervous
Try:
- lowering speed in `pure_pursuit.yaml`
- increasing `lookahead_distance` a little
- tuning FTG danger distance and blend distance more gently

---

# 24. Files you will probably edit first

## LiDAR mount and TF
- `src/r2_tg30_race/launch/tg30_bringup.launch`

## Deadman button
- `src/r2_tg30_race/config/joystick_deadman.yaml`

## FTG tuning
- `src/r2_tg30_race/config/follow_the_gap.yaml`
- `src/r2_tg30_race/config/steering_modifier.yaml`

## Pure pursuit tuning
- `src/r2_tg30_race/config/pure_pursuit.yaml`

## Ackermann output tuning
- `src/r2_tg30_race/config/ackermann_bridge.yaml`

## Mux priorities
- `src/r2_tg30_race/config/twist_mux.yaml`

---

# 25. Very short cheat sheet

## Make a map
Turn ON:
- roscore
- tg30_bringup
- scan_cleanup
- mapping_gmapping
- RViz mapping

Turn OFF:
- localization_amcl
- racing_stack

## Localize
Turn ON:
- roscore
- tg30_bringup
- scan_cleanup
- localization_amcl
- RViz localization

Turn OFF:
- mapping_gmapping

## Race
Turn ON:
- roscore
- tg30_bringup
- scan_cleanup
- localization_amcl
- joy_node
- racing_stack
- RViz racing optional

Turn OFF:
- mapping_gmapping

---

# 26. Final advice for first real testing

For the first real test day:

1. test LiDAR only
2. test scan cleanup
3. test localization only
4. test joystick deadman only
5. test Ackermann output on a stand
6. test very slow racing in an open area
7. tune one thing at a time

That order saves a lot of frustration.

