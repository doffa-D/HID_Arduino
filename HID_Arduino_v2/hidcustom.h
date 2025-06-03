#include <hidboot.h>
#include "ImprovedMouse.h"

#define CHECK_BIT(var, pos) ((var)&pos)

// Movement smoothing configuration
#define MOVEMENT_HISTORY_SIZE 3
#define MOVEMENT_THRESHOLD 5

// Updated to match HID descriptor format:
// - 5 buttons + 3 padding bits (1 byte)
// - X movement (12 bits, -2048 to 2047)
// - Y movement (12 bits, -2048 to 2047)
// - Wheel (8 bits, -127 to 127)
struct MYMOUSEINFO
{
    struct {
        uint8_t button1 : 1;
        uint8_t button2 : 1;
        uint8_t button3 : 1;
        uint8_t button4 : 1;
        uint8_t button5 : 1;
        uint8_t padding : 3;
    } buttons;
    
    // Raw movement data bytes
    uint8_t xLow;
    uint8_t xHigh;
    uint8_t yLow;
    uint8_t yHigh;
    uint8_t wheel;
};

class MouseRptParser : public MouseReportParser
{
public:
    MouseRptParser() {
        // Initialize previous button state to zero
        prevButtonsRaw = 0;
        // Initialize previous state to zeros for accurate button change detection
        memset(prevState.bInfo, 0, sizeof(prevState.bInfo));
        // Initialize movement history to zero
        moveHistory.index = 0;
        for (int i = 0; i < MOVEMENT_HISTORY_SIZE; ++i) {
            moveHistory.x[i] = 0;
            moveHistory.y[i] = 0;
        }
    }
private:
    // Raw previous button byte for click detection
    uint8_t prevButtonsRaw;
    union
    {
        MYMOUSEINFO mouseInfo;
        uint8_t bInfo[sizeof(MYMOUSEINFO)];
    } prevState;

    // Movement history for smoothing
    struct {
        int16_t x[MOVEMENT_HISTORY_SIZE];
        int16_t y[MOVEMENT_HISTORY_SIZE];
        uint8_t index;
    } moveHistory;

    // Helper functions for movement processing
    int16_t processMovement(uint8_t low, uint8_t high);
    int16_t smoothMovement(int16_t newValue, int16_t* history);
    void updateMovementHistory(int16_t x, int16_t y);

protected:
    void Parse(USBHID *hid, bool is_rpt_id, uint8_t len, uint8_t *buf);
    void OnMouseMove(MYMOUSEINFO *mi);
    void OnWheelMove(MYMOUSEINFO *mi);
};
