#include "ImprovedMouse.h"

#define BUTTON_LEFT    0x01  // Bit 0 (1)
#define BUTTON_RIGHT   0x02  // Bit 1 (2)
#define BUTTON_MIDDLE  0x04  // Bit 2 (4)
#define BUTTON_BACK    0x08  // Bit 3 (8)
#define BUTTON_FORWARD 0x10  // Bit 4 (16)

static const uint8_t _hidMultiReportDescriptorMouse[] PROGMEM = {
    // Based on the provided HID descriptor
    0x05, 0x01,        // Usage Page (Generic Desktop)
    0x09, 0x02,        // Usage (Mouse)
    0xA1, 0x01,        // Collection (Application)
    0x85, 0x01,        // Report ID (1)
    0x09, 0x01,        // Usage (Pointer)
    0xA1, 0x00,        // Collection (Physical)
    
    // Button report
    0x05, 0x09,        // Usage Page (Button)
    0x19, 0x01,        // Usage Minimum (Button 1)
    0x29, 0x05,        // Usage Maximum (Button 5)
    0x15, 0x00,        // Logical Minimum (0)
    0x25, 0x01,        // Logical Maximum (1)
    0x95, 0x05,        // Report Count (5)
    0x75, 0x01,        // Report Size (1)
    0x81, 0x02,        // Input (Data,Var,Abs)
    0x95, 0x01,        // Report Count (1)
    0x75, 0x03,        // Report Size (3)
    0x81, 0x01,        // Input (Cnst,Ary,Abs)

    // X/Y movement
    0x05, 0x01,        // Usage Page (Generic Desktop)
    0x09, 0x30,        // Usage (X)
    0x09, 0x31,        // Usage (Y)
    0x16, 0x00, 0xF8,  // Logical Minimum (-2048)
    0x26, 0xFF, 0x07,  // Logical Maximum (2047)
    0x75, 0x0C,        // Report Size (12)
    0x95, 0x02,        // Report Count (2)
    0x81, 0x06,        // Input (Data,Var,Rel)

    // Wheel movement
    0x09, 0x38,        // Usage (Wheel)
    0x15, 0x81,        // Logical Minimum (-127)
    0x25, 0x7F,        // Logical Maximum (127)
    0x75, 0x08,        // Report Size (8)
    0x95, 0x01,        // Report Count (1)
    0x81, 0x06,        // Input (Data,Var,Rel)

    0xC0,              // End Collection (Physical)
    0xC0               // End Collection (Application)
};

Mouse_::Mouse_(void)
{
  static HIDSubDescriptor node(_hidMultiReportDescriptorMouse, sizeof(_hidMultiReportDescriptorMouse));
  HID().AppendDescriptor(&node);
}

void Mouse_::begin(void)
{
  end();
}

void Mouse_::end(void)
{
  _buttons = 0;
  move(0, 0, 0);
}

void Mouse_::click(uint8_t b)
{
  _buttons = b;
  move(0, 0, 0);
  _buttons = 0;
  move(0, 0, 0);
}

void Mouse_::move(signed char x, signed char y, signed char wheel)
{
  HID_MouseReport_Data_t report;
  report.buttons = _buttons;
  report.xAxis = x;
  report.yAxis = y;
  report.wheel = wheel;
  SendReport(&report, sizeof(report));
}

void Mouse_::buttons(uint8_t b)
{
  if (b != _buttons)
  {
    _buttons = b;
    move(0, 0, 0);
  }
}

void Mouse_::press(uint8_t b)
{
  buttons(_buttons | b);
}

void Mouse_::release(uint8_t b)
{
  buttons(_buttons & ~b);
}

void Mouse_::releaseAll(void)
{
  _buttons = 0;
  move(0, 0, 0);
}

bool Mouse_::isPressed(uint8_t b)
{
  if ((b & _buttons) > 0)
    return true;
  return false;
}

void Mouse_::SendReport(void *data, int length)
{
  HID().SendReport(HID_REPORTID_MOUSE, data, length);
}

Mouse_ Mouse;
