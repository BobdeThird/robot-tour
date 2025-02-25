from pololu_3pi_2040_robot import robot
import time

# Robot parameters
wheel_diameter = 3.235  # Diameter of the robot's wheels in cm
encoder_count = 358.2  # Number of encoder counts per revolution
min_speed = 13.75  # Minimum speed in encoder counts per second

# PID constants
kp = 20  # Proportional gain
ki = 0.5  # Integral gain
kd = 10  # Derivative gain
integral_limit = 50  # Limit for integral term to prevent windup

motors = robot.Motors()
encoders = robot.Encoders()
display = robot.Display()
button_a = robot.ButtonA()
button_b = robot.ButtonB()
button_c = robot.ButtonC()

def cm_to_encoder_counts(cm):
    wheel_circumference = wheel_diameter * 3.14159
    return int((cm / wheel_circumference) * encoder_count)

def encoder_counts_to_cm(counts):
    wheel_circumference = wheel_diameter * 3.14159
    return (counts / encoder_count) * wheel_circumference

def calculate_dynamic_constant(distance_cm, time_expected):
    """
    Calculate the dynamic constant using the updated quadratic function:
    y = -0.07577x^2 + 0.61921x + 39.11896
    where x = scaled seconds = time_expected * (distance_cm / 120).
    """
    # Scale the time to adjust for the given distance
    scaled_seconds = time_expected * (abs(distance_cm) / 120)  # Use absolute distance
    # Use the quadratic function
    return -0.07577 * (scaled_seconds**2) + 0.61921 * scaled_seconds + 39.11896

def trapezoidal_velocity(current_time, total_time, distance_cm, dynamic_constant):
    """
    Calculate velocity using a trapezoidal profile with a perfect isosceles triangle.
    Adjusted with a dynamic constant.
    """
    # Calculate v_max and acceleration rate
    v_max = (2 * abs(distance_cm)) / total_time  # Use absolute distance
    acceleration_rate = v_max / (total_time / 2)

    if current_time < total_time / 2:
        # Acceleration phase
        current_speed = acceleration_rate * current_time
    elif current_time < total_time:
        # Deceleration phase
        current_speed = v_max - acceleration_rate * (current_time - total_time / 2)
    else:
        # Stop
        current_speed = 0

    # Ensure current speed does not drop below minimum speed
    current_speed = max(current_speed, min_speed if current_speed > 0 else 0)

    return dynamic_constant * current_speed

def move(distance_cm, time_expected, stop_motors=True):
    """
    Move the robot a given distance within the expected time using PID to stay straight.
    Supports both positive and negative distances.
    If stop_motors is True, the motors stop at the end of the movement.
    """

    
    # Determine direction of movement
    direction = 1 if distance_cm > 0 else -1

    # Use absolute distance for calculations
    abs_distance_cm = abs(distance_cm)
    target_counts = cm_to_encoder_counts(abs_distance_cm)
    encoders.get_counts(reset=True)  # Reset encoder counts

    # Calculate dynamic constant
    dynamic_constant = calculate_dynamic_constant(abs_distance_cm, time_expected)

    start_time = time.ticks_ms()
    integral = 0
    last_error = 0
    looped = False
    exit_reason = "None"  # Track the exit reason

    while True:
        # Update encoder counts
        left_count, right_count = encoders.get_counts()
        avg_count = abs((left_count + right_count) // 2)

        # Calculate elapsed time
        current_time = time.ticks_diff(time.ticks_ms(), start_time) / 1000.0

        # Check if target distance is reached or time is exceeded
        if avg_count >= target_counts:
            exit_reason = "Distance"
            break
        elif current_time >= time_expected:
            exit_reason = "Time"
            break

        # Calculate the PID error and correction
        error = direction * (left_count - right_count)  # Adjust error by direction
        integral += error
        integral = max(min(integral, integral_limit), -integral_limit)  # Clamp the integral term
        derivative = error - last_error
        correction = kp * error + ki * integral + kd * derivative

        # Calculate trapezoidal velocity using the dynamic constant
        base_speed = trapezoidal_velocity(current_time, time_expected, abs_distance_cm, dynamic_constant)

        # Adjust motor speeds based on PID correction and direction
        left_speed = direction * (base_speed - correction)
        right_speed = 1.075 *direction * (base_speed + correction)

        # Set motor speeds
        motors.set_speeds(left_speed, right_speed)

        # Display information
        display.fill(0)
        display.text(f"Distance: {encoder_counts_to_cm(avg_count):.2f} cm", 0, 0)
        display.text(f"Speed: {base_speed:.2f}", 0, 10)
        display.text(f"Error: {error}", 0, 20)
        display.text(f"Time: {current_time:.2f}s", 0, 30)
        display.text(f"Dyn const: {dynamic_constant:.2f}", 0, 40)
        display.show()

        # Update last error
        last_error = error
        looped = True

        time.sleep(0.025)

    motors.off()
    # Stop motors only if stop_motors is True
    # if stop_motors:
    #     motors.off()

    # Display completion
    if looped:
        display.fill(0)
        display.text(f"Distance: {encoder_counts_to_cm(avg_count):.2f} cm", 0, 0)
        display.text(f"Speed: {base_speed:.2f}", 0, 10)
        display.text(f"Error: {error}", 0, 20)
        display.text(f"Time: {current_time:.2f}s", 0, 30)
        display.text(f"Exited by: {exit_reason}", 0, 40)
        display.show()


# Main program loop
# while True:
#     if button_a.is_pressed():
#         time.sleep(0.5)
#         move(70, 2.2)  # Move 70 cm backward in 2.2 seconds