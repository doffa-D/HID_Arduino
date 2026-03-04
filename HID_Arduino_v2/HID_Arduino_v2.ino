#ifdef dobogusinclude
#include <spi4teensy3.h>
#endif

#include <SPI.h>
#include <usbhub.h>

#include "hidcustom.h"

// USB task timing
unsigned long lastUsbTask = 0;
const unsigned long USB_TASK_INTERVAL = 0; // No delay for maximum polling

// Mouse movement accumulation
int16_t accumulatedX = 0;
int16_t accumulatedY = 0;
int8_t accumulatedWheel = 0;
bool moveNeeded = false;

// Movement scaling and smoothing
const float BASE_SCALE = 1.0f;  // Base movement scale (1.0 = 1:1)
const float SPEED_SCALE = 0.4f; // Additional scaling for faster movements
const int16_t SPEED_THRESHOLD = 100; // Threshold for speed scaling
const float SPEED_MULTIPLIER = 1.0f; // Adjust this multiplier to change overall cursor speed (1.0 = same as normal mouse)

// Button mapping - based on the HID report descriptor
// Standard 5-button mouse uses bits 0-4 in the first byte
// Standard mapping: bit 0 = left, bit 1 = right, bit 2 = middle
// Side buttons are bits 3 and 4
#define BUTTON_LEFT    0x01  // Bit 0 (1)
#define BUTTON_RIGHT   0x02  // Bit 1 (2)
#define BUTTON_MIDDLE  0x04  // Bit 2 (4)
#define BUTTON_BACK    0x08  // Bit 3 (8)
#define BUTTON_FORWARD 0x10  // Bit 4 (16)

USB Usb;
USBHub Hub(&Usb);
HIDBoot<USB_HID_PROTOCOL_MOUSE> HidMouse(&Usb);
MouseRptParser Prs;

// Keep-alive to prevent USB suspend
unsigned long lastKeepAliveTime = 0;
constexpr unsigned long KEEP_ALIVE_MS = 1000;

void setup()
{
    Serial.begin(115200); // Start serial for Python communication
    Usb.Init();
    HidMouse.SetReportParser(0, &Prs);
    Mouse.begin();
}

void loop()
{
    // Process USB tasks immediately
    Usb.Task();

    // Send keep-alive to prevent USB bus suspension
    if (millis() - lastKeepAliveTime > KEEP_ALIVE_MS)
    {
        lastKeepAliveTime = millis();
        Mouse.move(0, 0, 0);
    }

    // Read serial commands
    static char cmdBuf[32];
    static uint8_t idx = 0;
    while (Serial.available())
    {
        char c = Serial.read();
        if (c == '\n' || c == '\r')
        {
            cmdBuf[idx] = '\0';
            if (idx > 0) handleCommand(cmdBuf);
            idx = 0;
        }
        else if (idx < 31)
        {
            cmdBuf[idx++] = c;
        }
    }

    // Apply accumulated movements when needed
    if (moveNeeded) {
        // Scale the accumulated values
        float scale = SPEED_MULTIPLIER;

        int16_t ax = accumulatedX;
        int16_t ay = accumulatedY;
        accumulatedX = 0;
        accumulatedY = 0;
        int8_t wheel = accumulatedWheel;
        accumulatedWheel = 0;
        moveNeeded = false;

        int8_t x8 = constrain((int)(ax * scale), -127, 127);
        int8_t y8 = constrain((int)(ay * scale), -127, 127);
        Mouse.move(x8, y8, wheel);
    }
}

// Smooth movement using moving average
int16_t MouseRptParser::smoothMovement(int16_t newValue, int16_t* history) {
    // Skip smoothing for small movements
    if (abs(newValue) < MOVEMENT_THRESHOLD) {
        return newValue;
    }
    
    // Update history and calculate average
    int32_t sum = newValue;
    for (int i = 0; i < MOVEMENT_HISTORY_SIZE - 1; i++) {
        sum += history[i];
        history[i] = history[i + 1];
    }
    history[MOVEMENT_HISTORY_SIZE - 1] = newValue;
    
    return (int16_t)(sum / MOVEMENT_HISTORY_SIZE);
}

void MouseRptParser::updateMovementHistory(int16_t x, int16_t y) {
    moveHistory.x[moveHistory.index] = x;
    moveHistory.y[moveHistory.index] = y;
    moveHistory.index = (moveHistory.index + 1) % MOVEMENT_HISTORY_SIZE;
}

void MouseRptParser::Parse(USBHID *hid, bool is_rpt_id, uint8_t len, uint8_t *buf)
{
    if (len < 6) return;
    
    // Get button byte directly (second byte of report)
    uint8_t btn = buf[1];

    // Process buttons using raw button byte
    ProcessButton((prevButtonsRaw & BUTTON_LEFT) != 0,  (btn & BUTTON_LEFT) != 0,  BUTTON_LEFT,   MOUSE_LEFT);
    ProcessButton((prevButtonsRaw & BUTTON_RIGHT) != 0, (btn & BUTTON_RIGHT) != 0, BUTTON_RIGHT,  MOUSE_RIGHT);
    ProcessButton((prevButtonsRaw & BUTTON_MIDDLE) != 0,(btn & BUTTON_MIDDLE) != 0,BUTTON_MIDDLE, MOUSE_MIDDLE);
    ProcessButton((prevButtonsRaw & BUTTON_BACK) != 0,  (btn & BUTTON_BACK) != 0,  BUTTON_BACK,   MOUSE_PREV);
    ProcessButton((prevButtonsRaw & BUTTON_FORWARD) != 0,(btn & BUTTON_FORWARD) != 0,BUTTON_FORWARD,MOUSE_NEXT);
    // Save current buttons for next comparison
    prevButtonsRaw = btn;

    // Process movement for 12-bit packed X and Y values
    // X value: uses buf[2] (LSB) and lower nibble of buf[3] (MSB)
    int16_t deltaX = (buf[2]) | ((buf[3] & 0x0F) << 8);
    // Sign extend X if negative (bit 11 is set)
    if (deltaX & 0x800) {
        deltaX |= 0xF000; // Extend to 16 bits
    }

    // Y value: uses upper nibble of buf[3] (LSB) and buf[4] (MSB)
    int16_t deltaY = ((buf[3] & 0xF0) >> 4) | (buf[4] << 4);
    // Sign extend Y if negative (bit 11 is set)
    if (deltaY & 0x800) {
        deltaY |= 0xF000; // Extend to 16 bits
    }

    if (deltaX != 0 || deltaY != 0) {
        // Directly accumulate movement (no smoothing)
        accumulatedX += deltaX;
        accumulatedY += deltaY;
        moveNeeded = true;
    }

    // Handle wheel movement directly
    int8_t wheelVal = (int8_t) buf[5];
    if (wheelVal != 0) {
        accumulatedWheel += wheelVal;
        moveNeeded = true;
    }
}

void MouseRptParser::OnMouseMove(MYMOUSEINFO *mi)
{
    // Movement is handled in Parse function
}

void MouseRptParser::OnWheelMove(MYMOUSEINFO *mi)
{
    accumulatedWheel += mi->wheel;
    moveNeeded = true;
}

// Process button state changes
inline void ProcessButton(bool prevPressed, bool newPressed, uint8_t buttonBit, uint8_t reportButton)
{
    if (prevPressed != newPressed)
    {
        if (newPressed)
            Mouse.press(reportButton);
        else
            Mouse.release(reportButton);
    }
}

// ============================================================================
// Serial Command Handlers
// ============================================================================

typedef void(*CmdFunc)(const char*);

struct CmdEntry { char code; CmdFunc fn; };

static void cmdClick(const char*) { Mouse.click(); }
static void cmdPress(const char*) { Mouse.press(MOUSE_LEFT); }
static void cmdRelease(const char*) { Mouse.release(MOUSE_LEFT); }
static void cmdMove(const char* params);
static void cmdStatus(const char*);

static const CmdEntry COMMANDS[] = {
    { 'c', cmdClick },
    { 'p', cmdPress },
    { 'r', cmdRelease },
    { 'm', cmdMove },
    { '?', cmdStatus },
};

static void handleCommand(const char *cmd)
{
    if (cmd[0] == '\0') return;

    for (const auto &e : COMMANDS)
    {
        if (cmd[0] == e.code)
        {
            e.fn(&cmd[1]);
            return;
        }
    }
}

static void cmdMove(const char *params)
{
    if (*params == '\0') return;
    char *endPtr;
    long x = strtol(params, &endPtr, 10);
    if (*endPtr != ',') return;
    long y = strtol(endPtr + 1, nullptr, 10);
    Mouse.move((int)x, (int)y, 0);
}

static void cmdStatus(const char *)
{
    Serial.println("OK");
}

