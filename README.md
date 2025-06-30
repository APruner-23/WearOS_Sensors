# How to start Backend python Server
In order to start the server, python3 should be installed in your device.

## 1. Clone the Repository
Clone this github repository by typing the following command:
`git clone https://github.com/APruner-23/WearOS_Sensors.git`

## 2. Install dependencies
Navigate to the Backend server directory by using the command:
`cd backend_server`
Install the dependencies in your virtual environment (recommended) or in your system by typing the following command:
`pip install -r requirements.txt`

## 3. Run the server
Run the server by typing the following command:
`python3 app.py`

Once done the server will be running on port 5000, and the smartwatch should be able to send data to it, if it is not able to send data it's probably because of firewall issues.

# List of available Sensors
- Accelerometer: Linear Acceleration along 3 axes (m/s^2)
- Magnetometer Sensor: Ambient Magnetic field 3 axes (microteslas)
- Orientation Sensor: Pitch, roll, yaw, deprecated
- Gyroscope: Angular velocity on 3 axes
- TCS3701 Light Sensor: Ambient light intensity
- Pressure Sensor: Atmospheric pressure (altitude estimation)
- Gravity Sensor: Force of gravity
- Linear Acceleration Sensor
- Rotation Vector Sensor
- Magnetometer Sensor-Uncalibrated
- Game Rotation Vector Sensor
- Gyroscope-Uncalibrated
- Step Detector: Generates an evenet each time a step is detected
- Step Counter: Cumulative count of steps taken since last reboot
- Geomagnetic Rotation Vector Sensor
- HeartRate
- TiltToWake: Detects tilting gestures (wake the screen)
- Stationary Sensor: Determines if the device is idle or in motion
- Instant Motion Sensor
- Low latency off body detect: Detects when the use removed his watch
- Accelerometer-Uncalibrated
- Imu Temperature: Temperature of the sensor
- Pressure Temperature Sensor 
- Magnetometer Temperature Sensor
- PPG Controller
- ECG Sensor
- ECG Lead Detector
- Gaze Sensor: Eye tracking
- Galvanic Skin Response: Electrical conductance of the skin (microsiemens), assess emotional arousal or stress levels
- Skin temperature sensor: Temperature of the skin
- PPG Sensor
- Step Cadence: Steps rate

For our use case we implemented in the app the data regarding HeartRate, Skin Temperature, Galvanic Skin Response, Ambient Light Intensity, PPG Sensor value, Accelerometer and Gyroscope.

# List of Trackable Exercises
In order to know what type of exercises we could track and take some information we run this code:
```
private fun monitorExercises() {
        lifecycleScope.launch {
            val capabilities = exerciseClient.getCapabilities()
            for (exerciseType in capabilities.supportedExerciseTypes) {
                Log.d("ExerciseCapabalities", "Supported exercise type: $exerciseType")
            }
        }
    }
```

The output is the following:
- ALPINE_SKIING
- BACKPACKING
- BACK_EXTENSION
- BADMINTON
- BARBELL_SHOULDER_PRESS
- BASEBALL
- BASKETBALL
- BENCH_PRESS
- BIKING
- BIKING_STATIONARY
- BOOT_CAMP
- BOXING
- BURPEE
- CALISTHENICS
- CRICKET
- CROSS_COUNTRY_SKIING
- CRUNCH
- DANCING
- DEADLIFT
- ELLIPTICAL
- EXERCISE_CLASS
- FENCING
- FOOTBALL_AMERICAN
- FOOTBALL_AUSTRALIAN
- FRISBEE_DISC
- GOLF
- GYMNASTICS
- HANDBALL
- HIGH_INTENSITY_INTERVAL_TRAINING
- HIKING
- HORSE_RIDING
- ICE_HOCKEY
- ICE_SKATING
- INLINE_SKATING
- JUMPING_JACK
- JUMP_ROPE
- LAT_PULL_DOWN
- LUNGE
- MARTIAL_ARTS
- MEDITATION
- MOUNTAIN_BIKING
- UNKNOWN
- ORIENTEERING
- PADDLING
- PARA_GLIDING
- PILATES
- PLANK
- RACQUETBALL
- ROCK_CLIMBING
- ROLLER_HOCKEY
- ROLLER_SKATING
- ROWING
- ROWING_MACHINE
- RUGBY
- RUNNING
- RUNNING_TREADMILL
- SAILING
- SCUBA_DIVING
- SKATING
- SKIING
- SNOWBOARDING
- SNOWSHOEING
- SOCCER
- SOFTBALL
- SQUASH
- SQUAT
- STAIR_CLIMBING
- STAIR_CLIMBING_MACHINE
- STRENGTH_TRAINING
- STRETCHING
- SURFING
- SWIMMING_OPEN_WATER
- SWIMMING_POOL
- TABLE_TENNIS
- TENNIS
- VOLLEYBALL
- WALKING
- WATER_POLO
- WEIGHTLIFTING
- WORKOUT
- YACHTING
- YOGA

Exercise tracking is not implemented in the current version of the app.

# Battery Consumption (Wear OS App)

2 Tests have been conducted on the Wear OS app to understand how impactful it is on the battery life.

Test 1 Server offline:
- Test time: 1 Hour, app always running
- Starting battery level: 95%
- End battery level: 72%
- Battery usage in 1 hour: -23%

Test 2 Server online:
- Test time: 1 Hour, app always running
- Starting battery level: 86%
- End battery level: 45%
- Battery usage in 1 hour: -41%
