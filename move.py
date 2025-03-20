from pololu_3pi_2040_robot import robot
import time
import machine

# Robot parameters
wheel_diameter = 3.235  # Diameter of the robot's wheels in cm
encoder_count = 358.2  # Number of encoder counts per revolution
min_speed = 13.75  # Minimum speed in encoder counts per second

# PID constants - base values for reference speed
kp_base = 20  # Proportional gain
ki_base = 0.5  # Integral gain
kd_base = 10  # Derivative gain
integral_limit = 50  # Limit for integral term to prevent windup

# Reference speed for PID scaling
reference_speed = 100  # Speed at which the base PID values are calibrated

# Ultrasonic sensor pins
TRIG_PIN = 27  # GP27
ECHO_PIN = 28  # GP28

# Configure ultrasonic pins
trigger = machine.Pin(TRIG_PIN, machine.Pin.OUT)
echo = machine.Pin(ECHO_PIN, machine.Pin.IN)

motors = robot.Motors()
encoders = robot.Encoders()
display = robot.Display()
button_a = robot.ButtonA()
button_b = robot.ButtonB()
button_c = robot.ButtonC()

def measure_distance():
    """
    Measure distance using HC-SR04 ultrasonic sensor.
    Returns distance in centimeters.
    """
    # Ensure trigger is low
    trigger.value(0)
    time.sleep_us(2)
    
    # Send 10us pulse to trigger
    trigger.value(1)
    time.sleep_us(10)
    trigger.value(0)
    
    # Wait for echo to go high
    timeout = 0
    while echo.value() == 0:
        timeout += 1
        if timeout > 30000:  # Timeout after ~30ms
            return -1  # Error - no echo received
    
    # Measure the time the echo pin stays high
    start = time.ticks_us()
    timeout = 0
    
    while echo.value() == 1:
        timeout += 1
        if timeout > 30000:  # Timeout after ~30ms
            return -2  # Error - echo too long
    
    end = time.ticks_us()
    
    # Calculate distance: Time * speed of sound / 2 (roundtrip)
    # Speed of sound is ~343m/s or 0.0343cm/µs
    duration = time.ticks_diff(end, start)
    distance = (duration * 0.0343) / 2
    
    return distance

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
    return -0.07577 * (scaled_seconds**2) + 0.61921 * scaled_seconds + 39.11896 + 0.05

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

def move(distance_cm, time_expected, stop_motors=True, target_ultrasound=None):
    """
    Move the robot a given distance within the expected time using PID to stay straight.
    Supports both positive and negative distances.
    If stop_motors is True, the motors stop at the end of the movement.
    If target_ultrasound is provided, acts as a reference point for accurate distance measurement.
    The acceleration curve will be identical whether or not ultrasound is used.
    Uses adaptive PID that scales with speed to ensure straight movement at all speeds.
    """
    
    # Determine direction of movement
    direction = 1 if distance_cm > 0 else -1

    # Use absolute distance for calculations
    abs_distance_cm = abs(distance_cm)
    target_counts = cm_to_encoder_counts(abs_distance_cm)
    encoders.get_counts(reset=True)  # Reset encoder counts

    # Calculate dynamic constant based on the intended distance and time
    # This ensures consistent acceleration regardless of ultrasound usage
    dynamic_constant = calculate_dynamic_constant(abs_distance_cm, time_expected)

    start_time = time.ticks_ms()
    integral = 0
    last_error = 0
    last_time = start_time
    looped = False
    exit_reason = "None"  # Track the exit reason
    
    # Initial distance measurement if using ultrasound
    initial_ultrasound = None
    if target_ultrasound is not None:
        initial_ultrasound = measure_distance()
        if initial_ultrasound < 0:  # Error reading sensor
            initial_ultrasound = None

    # Debug display counter
    display_counter = 0
    display_freq = 2  # Update display every 2 iterations to reduce overhead

    # For averaging correction values to reduce jitter
    correction_history = [0] * 3
    correction_idx = 0

    while True:
        # Update encoder counts
        left_count, right_count = encoders.get_counts()
        avg_count = abs((left_count + right_count) // 2)

        # Calculate time information
        current_time_ms = time.ticks_ms()
        current_time = time.ticks_diff(current_time_ms, start_time) / 1000.0
        dt = time.ticks_diff(current_time_ms, last_time) / 1000.0  # Time since last iteration in seconds
        last_time = current_time_ms

        # Check ultrasound ONLY for exit condition, if enabled
        current_ultrasound = None
        if target_ultrasound is not None:
            current_ultrasound = measure_distance()
            
            # Check if we've reached target ultrasound distance
            if current_ultrasound > 0:  # Valid reading
                if direction > 0:  # Moving forward
                    # Exit if ultrasound distance is less than or equal to target
                    if current_ultrasound <= target_ultrasound:
                        exit_reason = "Ultrasound"
                        break
                else:  # Moving backward
                    # Exit if ultrasound distance is greater than or equal to target
                    if current_ultrasound >= target_ultrasound:
                        exit_reason = "Ultrasound"
                        break

        # Check if target distance is reached based on encoders
        if avg_count >= target_counts:
            exit_reason = "Distance"
            break

        # Calculate velocity using trapezoidal profile based on elapsed time
        # This is ALWAYS calculated based on distance and time, not ultrasound
        if current_time < time_expected:
            base_speed = trapezoidal_velocity(current_time, time_expected, abs_distance_cm, dynamic_constant)
        else:
            # After expected time, use min_speed with the dynamic constant
            base_speed = min_speed * dynamic_constant

        # Calculate encoder counts per second (actual speed)
        counts_per_loop = abs(left_count + right_count) / 2  # Average counts in this loop
        counts_per_second = counts_per_loop / current_time if current_time > 0 else 0

        # Scale PID constants based on current speed
        # Higher speeds need more aggressive correction, lower speeds need gentler correction
        speed_ratio = base_speed / reference_speed if reference_speed > 0 else 1
        
        # Calculate adaptive PID constants
        # Power function with root for smoother transition - softens impact at very high speeds
        # while still providing stronger correction
        kp = kp_base * (speed_ratio ** 0.75)  # Less aggressive scaling for P term
        ki = ki_base * (speed_ratio ** 0.5)   # Even gentler for I term to prevent windup
        kd = kd_base * (speed_ratio ** 0.9)   # Strong scaling for D to dampen at high speeds
        
        # Safety caps on PID values to prevent extreme corrections
        kp = max(min(kp, kp_base * 3), kp_base * 0.5)
        ki = max(min(ki, ki_base * 2), ki_base * 0.3)
        kd = max(min(kd, kd_base * 4), kd_base * 0.7)

        # Calculate the PID error and correction
        error = direction * (left_count - right_count)  # Adjust error by direction
        
        # Scale integral and derivative calculations by dt for consistent behavior
        integral += error * dt
        integral = max(min(integral, integral_limit), -integral_limit)  # Clamp the integral term
        
        # Calculate derivative with respect to time for consistent behavior regardless of loop speed
        derivative = (error - last_error) / dt if dt > 0 else 0
        
        # Calculate correction with the adaptive PID constants
        correction = kp * error + ki * integral + kd * derivative
        
        # Apply a non-linear correction curve to prevent overcorrection at low speeds
        # and undercorrection at high speeds
        correction_magnitude = abs(correction)
        correction_sign = 1 if correction > 0 else -1
        if correction_magnitude > 0:
            # Apply a soft cap to prevent excessive corrections
            correction = correction_sign * min(correction_magnitude, base_speed * 0.3)
        
        # Add to history for smoothing
        correction_history[correction_idx] = correction
        correction_idx = (correction_idx + 1) % len(correction_history)
        
        # Use average correction for smoother response
        smoothed_correction = sum(correction_history) / len(correction_history)

        # Adjust motor speeds based on PID correction and direction
        left_speed = direction * (base_speed - smoothed_correction)
        right_speed = 1.075 * direction * (base_speed + smoothed_correction)
        
        # Apply safety limits to prevent any motor from going negative or too fast
        speed_limit = base_speed * 1.5  # 50% higher than base speed
        left_speed = max(min(left_speed, speed_limit), 0) if direction > 0 else min(max(left_speed, -speed_limit), 0)
        right_speed = max(min(right_speed, speed_limit), 0) if direction > 0 else min(max(right_speed, -speed_limit), 0)

        # Set motor speeds
        motors.set_speeds(left_speed, right_speed)

        # Update display less frequently to reduce overhead
        display_counter += 1
        if display_counter >= display_freq:
            display_counter = 0
            display.fill(0)
            
            if target_ultrasound is not None and current_ultrasound > 0:
                display.text(f"Ultra: {current_ultrasound:.1f}cm", 0, 0)
                display.text(f"Target: {target_ultrasound}cm", 0, 10)
            else:
                display.text(f"Dist: {encoder_counts_to_cm(avg_count):.1f}cm", 0, 0)
                display.text(f"Speed: {base_speed:.1f}", 0, 10)
            
            display.text(f"kP: {kp:.1f} E: {error}", 0, 20)
            display.text(f"Cor: {smoothed_correction:.1f}", 0, 30)
            display.text(f"L:{left_speed:.0f} R:{right_speed:.0f}", 0, 40)
            display.show()

        # Update last error
        last_error = error
        looped = True

        time.sleep(0.01)  # Faster loop for more responsive control

    # When exiting the loop, stop motors if required
    if stop_motors:
        motors.off()
    else:
        # Just set the speeds to 0 but don't turn off
        motors.set_speeds(0, 0)
    
    # Display completion
    if looped:
        display.fill(0)
        display.text(f"Dist: {encoder_counts_to_cm(avg_count):.2f}cm", 0, 0)
        if target_ultrasound is not None and current_ultrasound > 0:
            display.text(f"Ultra: {current_ultrasound:.1f}cm", 0, 10)
        display.text(f"Time: {current_time:.2f}s", 0, 20)
        display.text(f"Exit: {exit_reason}", 0, 30)
        display.show()


# Main program loop
# while True:
#     if button_a.is_pressed():
#         time.sleep(0.5)
#         move(70, 2.2)  # Move 70 cm backward in 2.2 seconds