from pololu_3pi_2040_robot import robot
import time
import machine

# Initialize robot display
display = robot.Display()
button_a = robot.ButtonA()

# Set up ultrasonic sensor pins
TRIG_PIN = 27  # GP27
ECHO_PIN = 28  # GP28

# Configure pins
trigger = machine.Pin(TRIG_PIN, machine.Pin.OUT)
echo = machine.Pin(ECHO_PIN, machine.Pin.IN)

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

def display_distance(distance):
    """
    Display the measured distance on the robot's screen.
    """
    display.fill(0)  # Clear display
    
    if distance < 0:
        # Display error message
        display.text("Sensor Error", 0, 0)
        display.text(f"Code: {int(distance)}", 0, 10)
    else:
        # Display distance
        display.text("Distance:", 0, 0)
        display.text(f"{distance:.1f} cm", 0, 10)
        
        # Visual indicator - bar gets shorter as objects get closer
        bar_max = 128  # Max width of display
        bar_length = min(int(distance * 2), bar_max)
        if bar_length > 0:
            display.rect(0, 25, bar_length, 10, 1)
    
    display.show()

def main():
    print("Ultrasonic Distance Sensor Test")
    print("Press Button A to exit")
    
    while not button_a.is_pressed():
        # Measure distance
        distance = measure_distance()
        
        # Display distance
        display_distance(distance)
        
        # Small delay between measurements
        time.sleep(0.1)
    
    # Clear display when exiting
    display.fill(0)
    display.text("Program ended", 0, 0)
    display.show()

# Run the main program
while True:
    if robot.ButtonA().is_pressed():
        time.sleep(0.5)  # Delay to ensure initialization
        main()
