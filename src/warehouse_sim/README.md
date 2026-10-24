# warehouse_sim

Group 22, Intelligent Robotics final project: a warehouse robot that explores an unknown warehouse.

This package is **Part 1: simulation environment and robot** (Yichen Wang). Everything for Part 1 lives here.

---

## 1. Structure

`warehouse_sim` is a normal ROS 2 package inside the `src/` folder of this repository. The repository root is the colcon workspace.

```
warehouse/                            <- repository root = colcon workspace
├── .gitignore                        <- ignores build/ install/ log/
└── src/
    ├── warehouse_sim/                <- Part 1 package (ament_python)
    │   ├── README.md                 <- this file
    │   ├── package.xml               <- package info and run dependencies
    │   ├── setup.py                  <- installs worlds/, models/, launch/
    │   ├── setup.cfg
    │   ├── resource/warehouse_sim
    │   ├── warehouse_sim/            <- Python module (empty for now)
    │   ├── test/                     <- default ROS 2 style checks
    │   ├── worlds/
    │   │   └── warehouse_a.sdf       <- warehouse world A
    │   ├── models/
    │   │   └── warehouse_robot/
    │   │       ├── model.sdf         <- the robot (body, wheels, sensors, drive plugin)
    │   │       └── model.config
    │   └── launch/
    │       └── warehouse_robot.launch.py   <- starts world + robot + ROS bridge
    └── ... (other folders are not ROS packages; colcon skips them)
```

Part 1 files:

| What | File |
|---|---|
| Warehouse world | `src/warehouse_sim/worlds/warehouse_a.sdf` |
| Robot model | `src/warehouse_sim/models/warehouse_robot/model.sdf` |
| One-command launch | `src/warehouse_sim/launch/warehouse_robot.launch.py` |

---

## 2. How to run

Tested on Ubuntu 26.04, ROS 2 Lyrical, Gazebo Jetty. The files avoid absolute paths and version-specific plugin names, so they should also run on the course setup (ROS 2 Jazzy, Gazebo Harmonic).

Requirements: `ros-<distro>-ros-gz` (Gazebo + ROS bridge) and, for driving by keyboard, `ros-<distro>-teleop-twist-keyboard`.

**Build** (from the repository root):

```bash
cd warehouse
colcon build
source install/setup.bash
```

Re-run `colcon build` after changing any file in `src/`. Files are used from `install/`, not `src/`.

**Start the world and the robot:**

```bash
ros2 launch warehouse_sim warehouse_robot.launch.py
```

**Drive the robot** (in a second terminal, after `source install/setup.bash`):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Keep the teleop terminal focused. `i` forward, `j`/`l` turn, `k` stop.

**Launch arguments:**

| Argument | Default | Meaning |
|---|---|---|
| `world` | `warehouse_a.sdf` | World file name inside `worlds/` |
| `x` | `-4.0` | Robot start x (m) |
| `y` | `0.0` | Robot start y (m) |
| `yaw` | `0.0` | Robot start heading (rad), 0 = facing +x |

Example, different start pose:

```bash
ros2 launch warehouse_sim warehouse_robot.launch.py x:=-5.0 y:=-1.0 yaw:=1.57
```

The launch file does four things:

1. Starts Gazebo with the chosen world (`-r` = start running immediately).
2. Spawns `models/warehouse_robot/model.sdf` at (`x`, `y`, `yaw`) with `ros_gz_sim create`.
3. Runs `ros_gz_bridge` to connect Gazebo topics to ROS 2 (list below).
4. Publishes static TFs from `base_link` to each sensor frame.

---

## 3. ROS 2 interface

All topics use simulation time (`/clock`), so ROS nodes should set `use_sim_time:=true`.

| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | ROS → Gazebo | Drive command |
| `/odom` | `nav_msgs/msg/Odometry` | Gazebo → ROS | Wheel odometry, 20 Hz |
| `/tf` | `tf2_msgs/msg/TFMessage` | Gazebo → ROS | `odom` → `base_link` |
| `/scan` | `sensor_msgs/msg/LaserScan` | Gazebo → ROS | 2D lidar |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | Gazebo → ROS | RGB camera |
| `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | Gazebo → ROS | |
| `/thermal/image_raw` | `sensor_msgs/msg/Image` | Gazebo → ROS | Thermal (infrared) camera |
| `/thermal/camera_info` | `sensor_msgs/msg/CameraInfo` | Gazebo → ROS | |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo → ROS | Simulation time |

**TF tree:**

```
odom ──> base_link ──> lidar_link
                  ├──> camera_link
                  └──> thermal_link
```

- `odom` → `base_link` comes from the DiffDrive plugin (via the bridge).
- `base_link` → sensors are static TFs published by the launch file.
- `base_link` is on the ground, centred between the wheels. There is no `base_footprint`, so for slam_toolbox / Nav2 set `base_frame: base_link`.
- No `map` frame yet: SLAM (Part 2) should publish `map` → `odom`.

---

## 4. Robot parameters

Round differential-drive robot. All values are in `models/warehouse_robot/model.sdf`.

Coordinates below are relative to `base_link` (x forward, y left, z up), in metres.

**Body and wheels**

| Part | Shape | Size | Position (x, y, z) | Mass |
|---|---|---|---|---|
| Chassis | Cylinder | radius 0.18, height 0.11 (0.06–0.17 m above ground) | (0, 0, 0.115) | 2.0 kg |
| Left wheel | Cylinder | radius 0.08, width 0.04 | (0.04, 0.17, 0.08) | 0.3 kg |
| Right wheel | Cylinder | radius 0.08, width 0.04 | (0.04, -0.17, 0.08) | 0.3 kg |
| Rear caster | Sphere, frictionless | radius 0.04 | (-0.13, 0, 0.04) | 0.1 kg |

Overall footprint: about 0.38 m wide, 0.38 m long. The narrowest aisle in world A is 1.4 m.

**Drive (DiffDrive plugin)**

| Parameter | Value |
|---|---|
| Wheel separation | 0.34 m |
| Wheel radius | 0.08 m |
| Max linear speed | ±0.5 m/s |
| Max angular speed | ±1.0 rad/s |
| Odometry rate | 20 Hz |

If you change the wheel size or position, update `wheel_separation` / `wheel_radius` in the DiffDrive plugin as well, or the odometry will be wrong.

---

## 5. Sensors

All sensors are currently **noise-free**. Gaussian noise can be added in each `<sensor>` block if needed.

### 2D LiDAR (`lidar_link`, topic `/scan`)

| Parameter | Value |
|---|---|
| Type | `gpu_lidar` |
| Position | (0, 0, 0.21), top centre of the robot |
| Field of view | 360° |
| Samples | 360 (1° resolution) |
| Range | 0.12 – 10.0 m |
| Update rate | 10 Hz |

The scan plane is at 0.21 m on purpose: the racks in world A have a solid base 0.3 m high, so a lidar mounted below 0.3 m sees them as walls. If you raise the lidar above 0.3 m it will see through the racks.

### RGB camera (`camera_link`, topic `/camera/image_raw`)

| Parameter | Value |
|---|---|
| Type | `camera` |
| Position | (0.185, 0.04, 0.13), front, left of centre |
| Resolution | 640 × 480, `R8G8B8` |
| Horizontal FOV | 1.047 rad (60°) |
| Clip range | 0.05 – 20 m |
| Update rate | 15 Hz |

### Thermal camera (`thermal_link`, topic `/thermal/image_raw`)

| Parameter | Value |
|---|---|
| Type | `thermal` |
| Position | (0.185, -0.04, 0.13), front, right of centre |
| Resolution | 320 × 240, 8-bit greyscale (`L8`), brighter = hotter |
| Horizontal FOV | 1.047 rad (60°) |
| Temperature range | 253.15 – 673.15 K, 3 K per grey level |
| Clip range | 0.1 – 20 m |
| Update rate | 10 Hz |

In Gazebo, every object is at ambient temperature unless it is given a temperature. To make an object hot, add this inside its `<visual>`:

```xml
<plugin filename="gz-sim-thermal-system" name="gz::sim::systems::Thermal">
  <temperature>350.0</temperature>
</plugin>
```

---

## 6. World A (`worlds/warehouse_a.sdf`)

World origin is the centre of the warehouse. All objects are static.

| Element | Details |
|---|---|
| Interior | 14 × 10 m (x −7…7, y −5…5), walls 0.2 m thick, 2 m high |
| Racks | 3 yellow racks, 6 m long, along y, at x = 1.5, 3.5, 5.5 (y −3…3); solid base 0.3 m high, 1.4 m aisles between them |
| Pallet stacks | (−5.5, 2.8), (−3, 2.8), (−5.5, −2.8), (5, 4.2) |
| Floor markings | Visual only (no collision): yellow/black bays, green lane lines |
| Default robot start | (−4, 0), facing +x |

Cartons on the racks are visual only: they have no collision and are not seen by the lidar.

The world includes the `gz-sim-sensors-system` plugin. **Any new world must include it too**, or the lidar and cameras will publish nothing:

```xml
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
  <render_engine>ogre2</render_engine>
</plugin>
```

---

## 7. How to change things

| I want to... | Edit | Also update |
|---|---|---|
| Move or resize a sensor | `<pose>` of that link in `model.sdf` | The matching `static_tf(...)` line in `warehouse_robot.launch.py` |
| Change sensor resolution / range / rate | That `<sensor>` block in `model.sdf` | Nothing |
| Change wheel size or spacing | Wheel links in `model.sdf` | `wheel_radius` / `wheel_separation` in the DiffDrive plugin |
| Change speed limits | DiffDrive plugin in `model.sdf` | Nothing |
| Add a new ROS topic from Gazebo | `bridge` arguments in `warehouse_robot.launch.py` | Nothing |
| Add a new world | Put the `.sdf` in `worlds/` (with the Sensors plugin) | Run with `world:=<file>.sdf` |

After any change: `colcon build`, then `source install/setup.bash`.

Portability rules (so the files run on both Jazzy/Harmonic and Lyrical/Jetty):

- No absolute paths such as `/home/<user>/...`. Find files with `get_package_share_directory('warehouse_sim')`.
- `<sdf version="1.9">`.
- Plugin file names without version numbers, e.g. `gz-sim-diff-drive-system`.
- Every `<pose>` needs 6 numbers: `x y z roll pitch yaw`.
