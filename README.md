[README_real_car_full_rewrite.md](https://github.com/user-attachments/files/25973376/README_real_car_full_rewrite.md)
[README_real_car_full_rewrite.md](https://github.com/user-attachments/files/25973376/README_real_car_full_rewrite.md)
# ROSMASTER R2 TG30 Race Course README

This README is written to help you run the car on the real vehicle step by step.

It is written in simple language on purpose.

This package is a **separate workspace**. It is made so you do **not** mess up your older ROS workspaces.

---

# 1. What this package does

This package helps your ROSMASTER R2 do four big jobs:

1. **Bring up the car sensors and joystick**
2. **Map** a driveway or sidewalk area
3. **Save waypoints** for a driving path
4. **Race or drive the path** using:
   - **Pure Pursuit** to follow the path
   - **Follow The Gap (FTG)** to avoid obstacles in front of the car

The final output is:
- `/cmd_vel` for the robot motion command
- optional `/ackermann_cmd` for an Ackermann steering interface

---

# 2. Very important idea: what launch starts the car

For your real car, your normal car bring-up is:

```bash
roslaunch yahboomcar_nav laser_bringup.launch
```

For this README, that is the **official first launch** for the real car.

That means this command is the one that should bring up:
- the car base
- LiDAR
- joystick
- any Yahboom-side hardware pieces already working on your robot

## Important
Do **not** start a second LiDAR driver at the same time.

This package has a launch file called:

```bash
roslaunch r2_tg30_race tg30_bringup.launch
```

But for your real car, you should **not** use that as your main bring-up if `yahboomcar_nav laser_bringup.launch` is already handling the LiDAR and joystick.

The custom package launch files in this workspace use `start_driver:=false` by default, so they do **not** start a second LiDAR driver unless you force them to.

That is good.

---

# 3. Big picture: what should be ON and OFF

## A. Mapping mode
Turn ON:
- car + LiDAR + joystick bring-up
- scan cleanup
- gmapping
- RViz
- optional rosbag recording
- optional waypoint recorder if you want to save a path while driving

Turn OFF:
- AMCL localization
- racing stack
- pure pursuit
- FTG racing control

## B. Localization mode
Turn ON:
- car + LiDAR + joystick bring-up
- map server
- AMCL
- RViz

Turn OFF:
- gmapping
- waypoint recording unless you are making a new path
- racing stack unless you are ready to drive the saved path

## C. Racing mode
Turn ON:
- car + LiDAR + joystick bring-up
- scan cleanup
- waypoint path publisher
- pure pursuit
- FTG
- deadman switch
- cmd_vel gate
- steering modifier
- twist_mux
- optional Ackermann bridge
- RViz racing view

Turn OFF:
- gmapping
- AMCL unless you are using map-based localization at the same time and it is stable
- waypoint extractor unless you are making a new route

---

# 4. Workspace location

This workspace is meant to be separate, for example:

```bash
~/ws_r2_tg30_race_pkg
```

Go into it with:

```bash
cd ~/ws_r2_tg30_race_pkg
```

Build it with:

```bash
catkin_make
```

Source it in every new terminal you use for this package:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
```

## Important
Do **not** change your `.bashrc` unless you really want to.

This package was made so you can source it only when you want it.

---

# 5. Real car startup order

This is the order I recommend on the real car.

## Terminal 1 - Start ROS if needed
If you are using a normal single-computer setup and `roscore` is not already started by your car stack:

```bash
roscore
```

If your Yahboom launch already starts everything needed, you may not need a separate `roscore` terminal.

## Terminal 2 - Bring up the real car, LiDAR, and joystick

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

Wait a few seconds.

Now check that the important topics exist:

```bash
rostopic list
```

You want to see things like:
- `/scan`
- `/joy`
- `/odom`
- `/tf`

Check the LiDAR is alive:

```bash
rostopic echo -n 1 /scan
```

Check the joystick is alive:

```bash
rostopic echo -n 1 /joy
```

Check odometry exists:

```bash
rostopic echo -n 1 /odom
```

If one of those is missing, stop here and fix that first.

---

# 6. About the LiDAR tilt and TF

This package assumes:
- LiDAR is about **4 to 5 inches above the ground**
- LiDAR is tilted down about **5 degrees**
- transform is about:
  - `x = 0.20`
  - `y = 0.0`
  - `z = 0.1143`
  - pitch = `-5°`

The custom launch files include a static transform through `tg30_bringup.launch`.

Because `mapping_gmapping.launch`, `localization_amcl.launch`, and `racing_stack.launch` include `tg30_bringup.launch` with `start_driver:=false`, they are mainly using it for the static TF, not for starting another LiDAR driver.

## Watch out for duplicate TF
If your Yahboom stack already publishes the **same exact** `base_link -> lidar_link` transform, you may get duplicate TF warnings.

If that happens, use only one source of that transform.

---

# 7. Mapping mode: make a map

Use this when you want to build a map of the driveway or sidewalk.

## Terminal 1
If needed:

```bash
roscore
```

## Terminal 2
Start the real car and LiDAR:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

## Terminal 3
Start gmapping and scan cleanup:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch r2_tg30_race mapping_gmapping.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
```

What this does:
- uses `/scan`
- filters the scan
- turns the scan into a cloud
- slices it back into `/scan_obstacles`
- feeds `/scan_obstacles` into gmapping

## Terminal 4
Open RViz:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch r2_tg30_race view_mapping.launch
```

## What to look for in RViz
You want to see:
- map growing as the car moves
- scan points lining up with walls, driveway edges, curb edges, etc.
- TF looking stable

## How to drive while mapping
Drive slowly.

Good first habits:
- do one slow lap
- do a second lap to clean up the map
- avoid very fast turns
- avoid jerky stopping and starting
- avoid too much grass clutter if the tilted LiDAR sees too much ground

## Save the map
When the map looks good:

```bash
mkdir -p ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps
rosrun map_server map_saver -f ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course
```

That makes files like:
- `driveway_course.pgm`
- `driveway_course.yaml`

---

# 8. Record a rosbag while driving

This is a very good idea.

A rosbag lets you replay the run later without driving the car again.

## Terminal 5

```bash
mkdir -p ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags
rosbag record -O ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags/driveway_run.bag /scan /tf /odom /joy /cmd_vel
```

If you also have IMU:

```bash
rosbag record -O ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags/driveway_run.bag /scan /tf /odom /imu /joy /cmd_vel
```

Stop recording with:

```bash
Ctrl+C
```

---

# 9. Save waypoints while driving

Use this when you want to make a path for pure pursuit.

## Terminal 5 or a new terminal
Run the waypoint recorder:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
rosrun r2_tg30_race waypoint_extractor.py _yaml_file:=/home/$USER/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml _path_topic:=/waypoint_path _sample_distance:=0.40
```

What this does:
- listens to `/odom`
- drops a new waypoint every `0.40` meters
- saves the YAML file again and again while you drive

## Optional manual mark button
The node can also listen to:

```bash
/waypoint_mark
```

If you publish to that topic, it adds a waypoint right then.

Example:

```bash
rostopic pub /waypoint_mark std_msgs/Empty -1
```

---

# 10. Very important: closed-loop path question

## Do you need to copy the first waypoint to the end?

For **this exact package**, the answer is usually **yes** if you want the car to keep driving in a loop.

Why?

Because the current `pure_pursuit_twist.py` node treats the **last waypoint** like the finish line.
When it gets close enough to the last point, it publishes a zero command and stops.

So:
- if you want a **one-way path**, do **not** add the first point at the end
- if you want a **closed loop race course**, usually **add the first waypoint again at the end**

## Where this comes from in the code
The current pure pursuit node does this logic:
- find target point
- if target is the last point
- and the robot is close enough
- publish `Twist()` which means stop

So if your path is supposed to be a loop, you need to close the loop yourself in the waypoint file.

## How to do it
Open the waypoint file:

```bash
nano ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml
```

You will see something like:

```yaml
frame_id: map
sample_distance: 0.4
waypoints:
  - x: 0.0
    y: 0.0
    yaw: 0.0
  - x: 1.0
    y: 0.0
    yaw: 0.0
  - x: 1.5
    y: 0.5
    yaw: 0.3
```

If the first waypoint is:

```yaml
  - x: 0.0
    y: 0.0
    yaw: 0.0
```

then copy that same point to the **end** of the waypoint list.

Example:

```yaml
frame_id: map
sample_distance: 0.4
waypoints:
  - x: 0.0
    y: 0.0
    yaw: 0.0
  - x: 1.0
    y: 0.0
    yaw: 0.0
  - x: 1.5
    y: 0.5
    yaw: 0.3
  - x: 0.0
    y: 0.0
    yaw: 0.0
```

Save the file.

## Small warning
Do not use a bad final point.

The last point should make sense.

Best practice:
- use the first point again at the end for a simple loop
- or use a last point that is very close to the first point and has a matching yaw

If the last point is far away or the yaw is strange, the car may make a weird turn at the loop join.

---

# 11. Publish the saved waypoint path

This package turns your YAML file into a `nav_msgs/Path` on `/race_path`.

The racing launch starts this automatically.

If you want to test it by itself:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
rosrun r2_tg30_race waypoint_map_builder.py _yaml_file:=/home/$USER/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml _path_topic:=/race_path
```

Then check:

```bash
rostopic echo -n 1 /race_path
```

---

# 12. Localization mode: use a saved map

Use this after you already have a map.

## Terminal 1
If needed:

```bash
roscore
```

## Terminal 2
Bring up the real car:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

## Terminal 3
Start AMCL with your saved map:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false map_file:=/home/$USER/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course.yaml scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
```

## Terminal 4
Open RViz:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch r2_tg30_race view_localization.launch
```

## What to do in RViz
Use **2D Pose Estimate** if needed to place the robot on the map.

Then slowly move the car a little.

AMCL is working better when:
- the scan lines up with the map
- the robot does not jump around
- the pose arrow stays believable

---

# 13. Racing mode: Pure Pursuit + FTG

This is the main path-following mode.

## What each part does

### Pure Pursuit
Pure Pursuit tries to follow the saved path.
It looks ahead to a point on the path and steers toward it.

### FTG (Follow The Gap)
FTG looks at the LiDAR and tries to find open space.
If something is in front of the car, FTG tries to steer around it.

### Steering Modifier
This node mixes Pure Pursuit and FTG.

Simple idea:
- clear path = mostly Pure Pursuit
- something close = blend toward FTG
- something very close = stop forward motion and let FTG turn away

### Deadman switch
The deadman switch is a safety hold-to-run button.
If you are not holding the button, the auto command should not keep driving the car.

### twist_mux
This picks which command wins.
In this package:
- safety has highest priority
- teleop is next
- auto is lower

So safety can override auto.

---

# 14. Racing mode startup order

## Terminal 1
If needed:

```bash
roscore
```

## Terminal 2
Bring up the real car:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

## Terminal 3
Start the racing stack:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch r2_tg30_race racing_stack.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles waypoint_yaml:=/home/$USER/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml use_ackermann_bridge:=true
```

## Terminal 4
Open RViz racing view:

```bash
source ~/ws_r2_tg30_race_pkg/devel/setup.bash
roslaunch r2_tg30_race view_racing.launch
```

---

# 15. Deadman switch: how it works

The deadman node uses:
- `/joy`
- button index `5`
- publishes enable to `/auto_enable`

In the config file:

```yaml
joy_topic: /joy
enable_topic: /auto_enable
deadman_button_index: 5
publish_hz: 30.0
joy_timeout: 0.75
```

That means:
- hold button **5** to allow auto drive
- if joystick messages stop for too long, auto disables

## Check the deadman signal

```bash
rostopic echo /auto_enable
```

Press and hold the deadman button.
You should see:

```bash
data: true
```

Release the button.
You should see:

```bash
data: false
```

If this does not happen, fix that before driving.

---

# 16. Command flow: how motion commands move through the system

This is the motion path in simple words.

## Path follower side
`waypoint_map_builder.py`
→ publishes `/race_path`

`pure_pursuit_twist.py`
→ reads `/race_path` and `/odom`
→ publishes `/cmd_vel_auto_raw`

## Safety gate side
`joy_deadman.py`
→ publishes `/auto_enable`

`cmdvel_gate.py`
→ blocks or allows `/cmd_vel_auto_raw`
→ outputs `/cmd_vel_auto`

## Obstacle side
`follow_the_gap.py`
→ reads `/scan_obstacles`
→ publishes `/cmd_vel_ftg_raw`

`steering_modifier.py`
→ mixes `/cmd_vel_auto` and `/cmd_vel_ftg_raw`
→ outputs `/cmd_vel_safety`

## Final command select
`twist_mux`
→ chooses among:
- `/cmd_vel_safety`
- `/cmd_vel_teleop`
- `/cmd_vel_auto`

→ final output is `/cmd_vel`

## Ackermann conversion
`twist_to_ackermann.py`
→ reads `/cmd_vel`
→ publishes `/ackermann_cmd`

---

# 17. Test the racing topics before moving the car

Before letting the car drive, check that the topics are alive.

## Check the path

```bash
rostopic echo -n 1 /race_path
```

## Check deadman enable

```bash
rostopic echo /auto_enable
```

## Check pure pursuit output

```bash
rostopic echo /cmd_vel_auto_raw
```

## Check gated auto output

```bash
rostopic echo /cmd_vel_auto
```

## Check FTG output

```bash
rostopic echo /cmd_vel_ftg_raw
```

## Check safety mixer output

```bash
rostopic echo /cmd_vel_safety
```

## Check final output

```bash
rostopic echo /cmd_vel
```

## Check Ackermann output

```bash
rostopic echo /ackermann_cmd
```

---

# 18. What to do before the first real drive

Put the car on a stand, or lift the wheels if possible.

Then:
1. start the racing stack
2. hold the deadman button
3. check `/auto_enable` becomes true
4. check `/cmd_vel` changes
5. check `/ackermann_cmd` changes
6. make sure steering direction is correct
7. make sure speed is not too high

Only after that should you test on the ground.

---

# 19. Important tuning files

These are the main files you will tune.

## Pure Pursuit
File:

```bash
~/ws_r2_tg30_race_pkg/src/r2_tg30_race/config/pure_pursuit.yaml
```

Current important values:
- `lookahead_distance: 0.65`
- `base_speed: 0.45`
- `max_speed: 0.70`

If the car wiggles too much:
- try a little bigger lookahead

If it cuts corners too much:
- lower speed
- or lower lookahead a little

## FTG
File:

```bash
~/ws_r2_tg30_race_pkg/src/r2_tg30_race/config/follow_the_gap.yaml
```

Current important values:
- `danger_distance: 0.85`
- `stop_distance: 0.35`
- `front_angle_deg: 85.0`

For sidewalk driving:
- increase `danger_distance` if you want the car to react earlier
- increase `stop_distance` if you want it to stop sooner

## Steering modifier
File:

```bash
~/ws_r2_tg30_race_pkg/src/r2_tg30_race/config/steering_modifier.yaml
```

This file controls how Pure Pursuit and FTG are blended.

If the car waits too long before avoiding obstacles:
- raise `danger_distance`
- maybe raise `blend_distance`

## Ackermann bridge
File:

```bash
~/ws_r2_tg30_race_pkg/src/r2_tg30_race/config/ackermann_bridge.yaml
```

Important values:
- `wheelbase: 0.26`
- `max_steering_angle: 0.45`
- `steering_sign: 1.0`

If steering is backwards:
- change `steering_sign` to `-1.0`

If the robot turns too hard:
- lower `max_steering_angle`

---

# 20. Replay a bag file later

You can replay a run without moving the real car.

## Terminal 1

```bash
roscore
```

## Terminal 2
Play the bag with clock:

```bash
rosbag play --clock ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags/driveway_run.bag
```

## Terminal 3
Run mapping, localization, or racing tools as needed.

Sometimes you also need simulated time:

```bash
rosparam set use_sim_time true
```

Then launch the package nodes.

---

# 21. Optional OctoMap

This package also has:

```bash
roslaunch r2_tg30_race octomap.launch
```

This uses `/scan_cloud` for optional 3D occupancy mapping.

Because your LiDAR is a 2D LiDAR with tilt, this can still give some useful 3D-ish obstacle information as the car moves, but it will not behave like a true 3D LiDAR.

---

# 22. Safe shutdown order

When you are done:

1. stop the racing or mapping launch first
2. stop RViz
3. stop rosbag recording
4. stop `yahboomcar_nav laser_bringup.launch`
5. stop `roscore` if you started it separately

This helps prevent half-written bag files and weird leftover topics.

---

# 23. Fast troubleshooting guide

## Problem: `/scan` is missing
Fix:
- check the LiDAR cable
- check power
- check that Yahboom bring-up really starts the LiDAR
- run:

```bash
rostopic list | grep scan
```

## Problem: `/joy` is missing
Fix:
- check joystick connection
- check joystick driver in Yahboom launch
- run:

```bash
rostopic echo -n 1 /joy
```

## Problem: `/odom` is missing
Fix:
- your car base driver is not publishing odometry yet
- Pure Pursuit needs `/odom`

## Problem: deadman never goes true
Fix:
- check button index `5`
- joystick may use a different button number on your hardware
- watch:

```bash
rostopic echo /joy
```

Then press buttons and see which one changes.

## Problem: car stops at the end of the path
Fix:
- for a loop track, add the first waypoint to the end of the waypoint file

## Problem: car turns the wrong way
Fix:
- change `steering_sign` in `ackermann_bridge.yaml`

## Problem: LiDAR sees too much ground clutter
Fix:
- adjust tilt a little
- adjust `scan_filters.yaml`
- adjust `pointcloud_to_laserscan.yaml`
- drive slower while mapping

## Problem: duplicate TF warning
Fix:
- make sure only one node publishes the same `base_link -> lidar_link` transform

---

# 24. Very important safety notes

Before real driving:
- test with wheels off the ground first
- keep speed low at first
- use open space
- keep one hand ready on stop
- do not trust the robot near people, cars, or roads until it is tested a lot
- do not start with full speed racing mode

Good first test speed is slow.

---

# 25. The most common real workflow

Here is the simplest real workflow.

## Step 1 - Bring up the car

```bash
roslaunch yahboomcar_nav laser_bringup.launch
```

## Step 2 - Make a map

```bash
roslaunch r2_tg30_race mapping_gmapping.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles
```

## Step 3 - Save the map

```bash
rosrun map_server map_saver -f ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_course
```

## Step 4 - Record waypoints while driving

```bash
rosrun r2_tg30_race waypoint_extractor.py _yaml_file:=/home/$USER/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml
```

## Step 5 - For a loop, add first waypoint to the end of the file

```bash
nano ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml
```

## Step 6 - Run the racing stack

```bash
roslaunch r2_tg30_race racing_stack.launch start_driver:=false scan_topic:=/scan obstacle_scan_topic:=/scan_obstacles waypoint_yaml:=/home/$USER/ws_r2_tg30_race_pkg/src/r2_tg30_race/waypoints/waypoints.yaml use_ackermann_bridge:=true
```

## Step 7 - Hold deadman button and test slowly

Watch:
- `/auto_enable`
- `/cmd_vel`
- `/ackermann_cmd`

---

# 26. Final answer to your waypoint question

Yes — with the way this package is currently coded, if you want a **continuous loop**, you should usually open `waypoints.yaml` and add the **first coordinate again at the end**.

That closes the path.

If you do **not** do that, the current Pure Pursuit node will usually treat the last waypoint like the finish line and stop there.

