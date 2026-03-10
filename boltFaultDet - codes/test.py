import serial
import time

# Change port as per your system (check in Device Manager or dmesg)
try:
    ser = serial.Serial('COM5', 9600, timeout=1)
    time.sleep(2)  # Wait for connection
    print("Connected to Arduino via TTL!\n")
    
    while True:
        msg = input("Enter message to send (or 'exit' to quit): ")
        if msg.lower() == 'exit':
            break
            
        ser.write((msg + '\n').encode())
        print("Sent:", msg)
        time.sleep(0.5)
        
        if ser.in_waiting > 0:
            response = ser.readline().decode().strip()
            print("Arduino:", response)
            
except serial.SerialException as e:
    print(f"Error connecting to serial port: {e}")
    print("Make sure:")
    print("1. Arduino is connected to COM5")
    print("2. No other program is using the port")
    print("3. Check Device Manager for correct port")
    
except KeyboardInterrupt:
    print("\nProgram interrupted by user")
    
finally:
    try:
        ser.close()
        print("Serial connection closed")
    except:
        pass