# ROSMASTER R2 TG30 Race Stack README

## Real car guide using your Yahboom bringup

This guide is written in simple words.
It is meant for the **real car**, not just simulation.

This version uses **your normal car bringup** as the first step:

```bash
roslaunch yahboomcar_nav laser_bringup.launch
```

In this guide, that command is treated as your main:
- **car bringup**
- **LiDAR bringup**
- **joystick bringup**

So when you use this command, you should **not** also start the package's own TG30 bringup launch.
That would try to start the LiDAR twice, which can cause problems.

---

# 1. What this package does

This package helps your ROSMASTER R2 do these jobs:

1. Turn your tilted TG30 scan into a cleaner obstacle scan
2. Make a map of driveway or sidewalk
3. Localize on that map later
4. Follow a saved path using **pure pursuit**
5. Use **follow the gap (FTG)** to help avoid obstacles
6. Use a **deadman switch** so the car only drives when you allow it
7. Convert the final command into an Ackermann-style steering command

---

# 2. The most important idea

Think of the system in two parts:

## Part A: Yahboom bringup
This is your car's normal base system.
It gives you the real hardware side.

Use:

```bash
roslaunch yahboomcar_nav laser_bringup.launch
```

We are treating that launch file as the thing that starts:
- the car base
- the LiDAR
- the joystick
- the main low-level hardware pieces you already trust

## Part B: the race package
This is the extra layer.
It adds:
- scan cleanup
- waypoint tools
- mapping
- localization
- pure pursuit
- FTG
- deadman gating
- mux behavior
- Ackermann bridge

---

# 3. Very important rule

## Do this
Use **your Yahboom bringup** as the first launch for the real car.

## Do NOT do this
Do **not** also run:

```bash
roslaunch r2_tg30_race tg30_bringup.launch
```

when `yahboomcar_nav laser_bringup.launch` is already running.

Why?
Because both can try to own the same LiDAR or publish the same scan.
That can break things.

---

# 4. The launch order in plain English

Here is the simple order:

## Always first
Start the real car and LiDAR with:

```bash
roslaunch yahboomcar_nav laser_bringup.launch
```

## Then start the race package pieces you need
Depending on what you are doing, you then start:

- `scan_cleanup.launch`
- `mapping_gmapping.launch`
- `localization_amcl.launch`
- `racing_stack.launch`
- RViz launch if you want to see things

---

# 5. What each mode means

## Mode 1: Bringup only
This is just to turn the car on and make sure basic hardware works.

## Mode 2: Mapping
This is when you drive around and build a map.

## Mode 3: Localization
This is when the car uses a saved map to figure out where it is.

## Mode 4: Racing / path following
This is when pure pursuit tries to follow the path and FTG helps avoid hitting things.

---

# 6. Before you start

Make sure these are true:

- The battery is charged
- The car is on the ground with space around it
- The TG30 is plugged in
- The joystick is connected
- ROS is installed and your workspace is built
- Your saved map exists if you want localization
- Your path or waypoint file exists if you want racing

Also:
- put the car on blocks or lift the drive wheels if you are doing first motor tests
- keep one hand ready to stop the car
- start with very low speeds

---

# 7. Build and source the workspace

Open a terminal and run:

```bash
cd ~/ws_r2_tg30_race_pkg
catkin_make
source devel/setup.bash
```

You may need to run `source devel/setup.bash` in each new terminal you open for this workspace.

---

# 8. Terminal plan for the real car

A very easy way to stay organized is to use separate terminals.

## Terminal 1 = real car bringup
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

This is now your official **car + lidar + joy bringup**.

## Terminal 2 = scan cleanup
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```

## Terminal 3 = mode-specific launch
Use one of these depending on your job:
- mapping
- localization
- racing

## Terminal 4 = RViz (optional)
Use if you want to watch the car and scan data.

---

# 9. Quick health check after bringup

After Terminal 1 is running, open a new terminal and check:

```bash
rostopic list
```

You want to see things like:
- `/scan`
- `/joy`
- `/tf`
- `/odom`

Then check the scan is alive:

```bash
rostopic echo /scan
```

Then check the joystick is alive:

```bash
rostopic echo /joy
```

If data is scrolling, that part is working.

---

# 10. Mapping mode

Use this when you want to create a new map.

## What should be ON
Turn ON:
- `roslaunch yahboomcar_nav laser_bringup.launch`
- `roslaunch r2_tg30_race scan_cleanup.launch`
- `roslaunch r2_tg30_race mapping_gmapping.launch`
- optional RViz mapping view

## What should be OFF
Turn OFF:
- `localization_amcl.launch`
- `racing_stack.launch`

## Exact order

### Terminal 1
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

### Terminal 2
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```

### Terminal 3
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race mapping_gmapping.launch start_driver:=false
```

`start_driver:=false` matters here because your driver is already started by the Yahboom bringup.

### Terminal 4 (optional)
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_mapping.launch
```

## What to do next
Now slowly drive the car around the driveway and sidewalk area.
Try to move in smooth paths.
Do not drive too fast.
Give gmapping time to build the map.

## Save the map when done
Open another terminal:

```bash
mkdir -p ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps
rosrun map_server map_saver -f ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/maps/driveway_map
```

This makes files like:
- `driveway_map.pgm`
- `driveway_map.yaml`

---

# 11. Localization mode

Use this after you already have a saved map.

## What should be ON
Turn ON:
- `roslaunch yahboomcar_nav laser_bringup.launch`
- `roslaunch r2_tg30_race scan_cleanup.launch`
- `roslaunch r2_tg30_race localization_amcl.launch`
- optional RViz localization view

## What should be OFF
Turn OFF:
- `mapping_gmapping.launch`
- `racing_stack.launch` if you are only testing localization

## Exact order

### Terminal 1
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

### Terminal 2
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```

### Terminal 3
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false
```

### Terminal 4 (optional)
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_localization.launch
```

## What to do in RViz
In RViz, look for:
- the map
- the LiDAR scan
- the robot pose

If the pose looks wrong, use **2D Pose Estimate** in RViz to give AMCL a starting guess.
Click on the map where the car really is.
Drag the arrow in the direction the car is facing.

## How to know localization is working
You are looking for this:
- the scan lines match the map walls and edges
- the robot pose stays stable
- the map and scan do not drift apart badly

---

# 12. Racing mode

Use this when you want the car to follow a path.

## What should be ON
Turn ON:
- `roslaunch yahboomcar_nav laser_bringup.launch`
- `roslaunch r2_tg30_race scan_cleanup.launch`
- `roslaunch r2_tg30_race localization_amcl.launch` or another good pose source
- `roslaunch r2_tg30_race racing_stack.launch`
- optional RViz racing view

## What should be OFF
Turn OFF:
- `mapping_gmapping.launch`

## Exact order

### Terminal 1
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

### Terminal 2
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```

### Terminal 3
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false
```

### Terminal 4
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race racing_stack.launch start_driver:=false
```

### Terminal 5 (optional)
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_racing.launch
```

---

# 13. What happens in racing mode

This is the easy version:

## Pure pursuit
Pure pursuit tries to follow the saved path.
You can think of it like the car looking a little ahead on the path and steering toward that point.

## FTG
Follow the gap looks at open space in front of the car.
If something blocks the path, FTG tries to help steer toward a safer open gap.

## Steering modifier / safety layer
This layer mixes the path-following command and the obstacle-avoid command.

## Deadman switch
The deadman switch says:
- if the button is held, auto is allowed
- if the button is not held, auto is blocked

## Mux
The mux decides which velocity command wins.
That helps keep safety commands organized.

## Ackermann bridge
At the end, the final `/cmd_vel` is converted into your steering and speed command.

---

# 14. Deadman switch in simple words

The deadman switch is your safety hold-to-run button.

That means:
- hold the button = car is allowed to move in auto
- let go = car should stop accepting the auto command

This is very important on the real car.

## Before testing movement
Lift the drive wheels or put the car in a safe open area.

## Check the enable signal
In a new terminal run:

```bash
rostopic echo /auto_enable
```

Now hold your deadman button.
You should see it change to `True`.
Let go and it should go back to `False`.

If it never changes, check:
- joystick is connected
- `/joy` is publishing
- deadman button index matches your joystick setup

---

# 15. RViz: what to turn on

RViz is the window that helps you see what the robot thinks.

## For mapping RViz
Use:

```bash
roslaunch r2_tg30_race view_mapping.launch
```

Turn on displays like:
- Map
- LaserScan
- TF
- RobotModel if available

## For localization RViz
Use:

```bash
roslaunch r2_tg30_race view_localization.launch
```

Look for:
- map
- scan matching the map
- robot pose

## For racing RViz
Use:

```bash
roslaunch r2_tg30_race view_racing.launch
```

Look for:
- race path
- scan obstacles
- robot pose
- path tracking behavior

---

# 16. Recording rosbags

Rosbags are like recordings of your robot topics.
They are very useful.

Use them when:
- mapping
- debugging FTG
- testing pure pursuit
- checking deadman behavior

## Manual rosbag record example
Open a new terminal:

```bash
mkdir -p ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags
cd ~/ws_r2_tg30_race_pkg/src/r2_tg30_race/bags
rosbag record /scan /scan_obstacles /tf /odom /joy /cmd_vel /ackermann_cmd
```

Press `Ctrl+C` when done.

---

# 17. Playing back a rosbag later

To replay a bag:

```bash
rosbag play your_file.bag --clock
```

If you replay data, make sure other live publishers are not fighting with the same topics unless that is what you want.

---

# 18. Waypoint recording idea

A simple way to make waypoints is to drive the car and save points from `/odom`.
That way you create a path from real motion.

You can later turn that into a path for pure pursuit.

If your waypoint tool is already included in your flow, run it in a separate terminal after bringup and scan cleanup.

---

# 19. What to turn OFF in each mode

## When mapping
Turn OFF:
- AMCL
- racing stack

## When localizing only
Turn OFF:
- gmapping
- racing stack if not testing drive

## When racing
Turn OFF:
- gmapping

## Always avoid this mistake
Do not run **gmapping and AMCL together** in normal real-car use.
One makes the map.
The other uses the map.
Running both together usually causes confusion.

---

# 20. First safe movement test

Do this slowly.

## Step 1
Start:
- Yahboom bringup
- scan cleanup
- localization if needed
- racing stack

## Step 2
Check topics:

```bash
rostopic list
```

Make sure you see:
- `/scan`
- `/scan_obstacles`
- `/joy`
- `/auto_enable`
- `/cmd_vel`
- `/ackermann_cmd`

## Step 3
Watch the final command

```bash
rostopic echo /ackermann_cmd
```

## Step 4
Hold the deadman button.
Only then should the car be allowed to move in auto.

## Step 5
Start with very low speed values.
Test in a very open area.

---

# 21. If the car does not move

Check these in order:

1. Is the Yahboom bringup running?
2. Is `/joy` publishing?
3. Is `/auto_enable` becoming `True` when you hold the button?
4. Is pure pursuit publishing?
5. Is FTG publishing?
6. Is `/cmd_vel` changing?
7. Is `/ackermann_cmd` changing?
8. Is your motor controller listening to the expected topic?

A good check is:

```bash
rostopic echo /cmd_vel
rostopic echo /ackermann_cmd
```

If `/cmd_vel` changes but the car does not move, the issue is usually after the mux, in the bridge or low-level motor side.

---

# 22. If the car steers the wrong way

That usually means one of these is wrong:
- steering sign
- wheelbase value
- frame direction assumption
- Ackermann bridge scaling

Open the config file for the bridge and steering settings and reverse the needed sign carefully.
Test at very low speed.

---

# 23. If FTG is too nervous on sidewalks

That usually means the danger distance is too big or the tilted scan still sees too much ground clutter.

What to do:
- lower FTG danger distance a little
- narrow the front danger zone
- improve scan cleanup
- reduce speed
- test in a wide sidewalk area first

Only change one thing at a time.
Then test again.

---

# 24. If mapping looks bad

Check these things:
- LiDAR is stable and mounted tightly
- `scan_cleanup.launch` is running
- `/scan_obstacles` looks cleaner than raw `/scan`
- odometry is healthy
- you are driving slowly and smoothly

Tilted LiDAR setups can work, but they need good filtering.

---

# 25. Best simple startup recipes

## Recipe A: just turn the car on and check hardware
### Terminal 1
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```

## Recipe B: make a map
### Terminal 1
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```
### Terminal 2
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```
### Terminal 3
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race mapping_gmapping.launch start_driver:=false
```
### Terminal 4
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_mapping.launch
```

## Recipe C: localize on a saved map
### Terminal 1
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```
### Terminal 2
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```
### Terminal 3
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false
```
### Terminal 4
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_localization.launch
```

## Recipe D: race path with obstacle avoidance
### Terminal 1
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch yahboomcar_nav laser_bringup.launch
```
### Terminal 2
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race scan_cleanup.launch
```
### Terminal 3
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race localization_amcl.launch start_driver:=false
```
### Terminal 4
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race racing_stack.launch start_driver:=false
```
### Terminal 5
```bash
cd ~/ws_r2_tg30_race_pkg
source devel/setup.bash
roslaunch r2_tg30_race view_racing.launch
```

---

# 26. Shutdown order

When done:

1. Stop the racing stack
2. Stop localization or mapping
3. Stop scan cleanup
4. Stop the Yahboom bringup last

A simple safe order is pressing `Ctrl+C` in the reverse order you started things.

---

# 27. Final simple rule

For your real car, remember this:

## This is your official first launch:
```bash
roslaunch yahboomcar_nav laser_bringup.launch
```

Then add the race package pieces after that.

## Do not also start:
```bash
roslaunch r2_tg30_race tg30_bringup.launch
```

because your Yahboom launch is now the bringup you want to use.

