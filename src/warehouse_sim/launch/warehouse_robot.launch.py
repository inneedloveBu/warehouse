"""Start a warehouse world, spawn the robot and bridge its topics to ROS 2.

Build the workspace first, then:
    ros2 launch warehouse_sim warehouse_robot.launch.py
    ros2 launch warehouse_sim warehouse_robot.launch.py x:=-5.0 y:=-1.0 yaw:=1.57

All files are found through the installed package share directory, so it
works on any machine (Jazzy/Harmonic or Lyrical/Jetty) without editing.
"""
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def static_tf(child, x, y, z):
    """Fixed sensor pose relative to base_link (same numbers as model.sdf)."""
    return Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name=f'{child}_tf',
        arguments=['--x', str(x), '--y', str(y), '--z', str(z),
                   '--frame-id', 'base_link', '--child-frame-id', child],
        parameters=[{'use_sim_time': True}],
    )


def generate_launch_description():
    pkg_share = get_package_share_directory('warehouse_sim')
    robot_sdf = os.path.join(pkg_share, 'models', 'warehouse_robot', 'model.sdf')

    # Which world to load and where the robot starts
    args = [
        DeclareLaunchArgument('world', default_value='warehouse_a.sdf',
                              description='World file in the worlds/ folder'),
        DeclareLaunchArgument('x', default_value='-4.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
    ]
    world = PathJoinSubstitution([pkg_share, 'worlds', LaunchConfiguration('world')])

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r ', world]}.items(),
    )

    # Put the robot into the running world
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'warehouse_robot', '-file', robot_sdf,
                   '-x', LaunchConfiguration('x'),
                   '-y', LaunchConfiguration('y'),
                   '-z', '0.0',
                   '-Y', LaunchConfiguration('yaw')],
        output='screen',
    )

    # ]  ROS -> Gazebo,  [  Gazebo -> ROS
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/thermal/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/thermal/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription(args + [
        gz_sim,
        spawn,
        bridge,
        static_tf('lidar_link', 0.0, 0.0, 0.21),
        static_tf('camera_link', 0.185, 0.04, 0.13),
        static_tf('thermal_link', 0.185, -0.04, 0.13),
    ])
