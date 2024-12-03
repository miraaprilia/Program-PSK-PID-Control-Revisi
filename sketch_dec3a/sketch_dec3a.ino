// Pin untuk kontrol motor  
const int IN1 = 8;   // Pin kontrol arah motor 1  
const int IN2 = 9;   // Pin kontrol arah motor 2  
const int ENA = 10;  // Pin untuk kontrol kecepatan motor (PWM)  

// Pin untuk encoder  
const int encoderPinA = 2; // Pin untuk Encoder A  
const int encoderPinB = 3;  

// Variabel untuk encoder  
volatile int direction = 0;  
volatile int pulseCount = 0;  // Menghitung jumlah pulse dari encoder  
unsigned long lastTime = 0;    // Waktu terakhir pembaruan  
float rpmValue = 0;            // Kecepatan dalam RPM  

const int PPR = 11;            // Pulsa per rotasi encoder  
const float GearRatio = 9.6;   // Rasio gear motor  

// PID Variables  
float kp = 0.18;      // Konstanta Proportional  
float ki = 0.1;       // Konstanta Integral  
float kd = 0.01;      // Konstanta Derivative  

float setpoint = 0; // RPM yang diinginkan (target RPM)  
float e = 0, e_prev = 0, inte = 0, inte_prev = 0; // Error, Integral, Derivative  
int pidOutput = 0;  // Output dari PID (tipe data int)  

bool isRunning = false; // Status motor  

void setup() {  
    Serial.begin(9600); // Inisialisasi komunikasi serial  
    pinMode(IN1, OUTPUT);  
    pinMode(IN2, OUTPUT);  
    pinMode(ENA, OUTPUT);  
    pinMode(encoderPinA, INPUT);  
    pinMode(encoderPinB, INPUT);  

    attachInterrupt(digitalPinToInterrupt(encoderPinA), countEncoder, RISING); // Interrupt untuk menghitung pulsa  
}  

void loop() {  
    unsigned long currentTime = millis();  
    int currentCount = pulseCount;  

    // Hitung RPM setiap 1000 ms  
    if (currentTime - lastTime >= 100) {  
        readSensor(); // Menghitung RPM  
        lastTime = currentTime;  

        if (isRunning) { // Only run PID control if the motor is running  
            pidOutput = PIDControl(); // Menghitung output PID  
            analogWrite(ENA, pidOutput);  // Sesuaikan PWM berdasarkan output PID  
        }  

        // Kirim data RPM ke GUI  
        Serial.print("RPM:");  
        Serial.println(int(rpmValue));    
        Serial.print("Dir:");  
        Serial.println(direction);  
        } else if (currentCount >= 0) {  
          Serial.println("STOP");  
        }  
      

    // Cek perintah dari serial  
    if (Serial.available() > 0) {  
        String command = Serial.readStringUntil('\n');  
        handleCommand(command);  
    }  
}  

// Fungsi interrupt untuk menghitung pulse encoder  
void countEncoder() {  
    pulseCount++;  

    // Membaca nilai pin B saat terjadi rising edge pada pin A  
    int stateB = digitalRead(encoderPinB);  

    // Menentukan arah berdasarkan nilai pin B  
    if (stateB == HIGH) {  
        direction = 1;  
    } else {  
        direction = -1;   
    }  
}  

// Fungsi untuk menghitung RPM berdasarkan pulse encoder  
void readSensor() {  
    rpmValue = (pulseCount / (PPR * GearRatio)) * 600; // Hitung RPM  
    pulseCount = 0; // Reset hitungan pulsa  
}  

// Fungsi untuk mengatur kecepatan motor menggunakan PID  
int PIDControl() {  
    e = setpoint - rpmValue;  // Error = target RPM - RPM saat ini  
    inte = inte_prev + e;  // Integral error  
    float derivative = e - e_prev;  // Derivative error  

    // Menghitung output PID  
    pidOutput = constrain(kp * e + ki * inte + kd * derivative, 0, 255); // Output PWM  

    // Simpan nilai error untuk perhitungan berikutnya  
    e_prev = e;  
    inte_prev = inte;  

    return pidOutput;  
}  

// Add these variables to store the parameters  
float storedKp = 0.18; // Default value for Kp  
float storedKi = 0.1;  // Default value for Ki  
float storedKd = 0.01; // Default value for Kd  
int storedSetpoint = 0; // Default target RPM  
bool storedDirection = true; // Default direction (CW)  

// Update the handleCommand function  
void handleCommand(String command) {  
    int delimiterIndex = command.indexOf('=');  
    if (delimiterIndex > 0) {  
        String param = command.substring(0, delimiterIndex);  
        String value = command.substring(delimiterIndex + 1);  

        if (param == "Kp") {  
            kp = value.toFloat();  
            storedKp = kp; // Store the updated value  
            Serial.println("Kp updated: " + String(kp));  
        
        } else if (param == "Ki") {  
            ki = value.toFloat();  
            storedKi = ki; // Store the updated value  
            Serial.println("Ki updated: " + String(ki));  
        } else if (param == "Kd") {  
            kd = value.toFloat();  
            storedKd = kd; // Store the updated value  
            Serial.println("Kd updated: " + String(kd));  
        } else if (param == "R") {  
            setpoint = value.toInt();  
            storedSetpoint = setpoint; // Store the updated value  
            Serial.println("Target RPM updated: " + String(setpoint));  
        } else if (param == "D") {  
            if (value == "CW") {  
                storedDirection = true; // Store direction  
                setMotorDirection(true);  
                Serial.println("Direction set to CW");  
            } else if (value == "CCW") {  
                storedDirection = false; // Store direction  
                setMotorDirection(false);  
                Serial.println("Direction set to CCW");  
            }  
        } else if (param == "C") {  
            if (value == "GO") {  
                isRunning = true; // Set the running status to true  
                CommandRun(true);  
                // Send stored values when GO command is received  
                Serial.print("GO Command Received. Parameters: ");  
                Serial.print("Kp: "); Serial.print(storedKp);  
                Serial.print(", Ki: "); Serial.print(storedKi);  
                Serial.print(", Kd: "); Serial.print(storedKd);  
                Serial.print(", RPM: "); Serial.print(storedSetpoint);  
                Serial.print(", Direction: "); Serial.println(storedDirection ? "CW" : "CCW");  
            } else if (value == "STOP") {  
                isRunning = false; // Set the running status to false  
                CommandRun(false); 
                analogWrite(ENA, 0); 
                Serial.println("Stopping System");  
            }  
        }    
    }  
}  

void CommandRun(bool go) {  
    if (go) {  
        setMotorDirection(storedDirection); // Use stored direction  
        // Reset PID output for starting  
        pidOutput = 0;   
    } else {  
        digitalWrite(IN1, LOW);  
        digitalWrite(IN2, LOW);  
        setpoint = 0; // Stop the motor  
        pidOutput = 0;   
    }  
}  

// Fungsi untuk mengatur arah motor  
void setMotorDirection(bool clockwise) {  
    if (clockwise) {  
        digitalWrite(IN1, HIGH);  
        digitalWrite(IN2, LOW);  
    } else {  
        digitalWrite(IN1, LOW);  
        digitalWrite(IN2, HIGH);  
    }  
}