# Dorm Guardian / Smart Room Guardian

A student portfolio project that combines embedded systems, backend development, computer vision, local data storage, and a live web dashboard into one smart room monitoring system.

The project currently runs as a Mac-based prototype and is designed to later move onto a Raspberry Pi.

## What it does

Dorm Guardian monitors a room using:

- STM32 sensor firmware
- BME280 temperature, humidity, and pressure readings
- BH1750 light readings
- USB serial data transfer
- Python serial collector
- SQLite local database
- FastAPI backend
- React + TypeScript dashboard
- OpenCV camera stream
- OpenCV motion detection
- Saved motion events
- Rule-based alerts

## Current status

Working MVP:

- STM32 reads real sensor data
- STM32 sends JSON over USB serial
- Python collector stores readings in SQLite
- FastAPI exposes sensor, camera, motion, and alert endpoints
- React dashboard displays live readings and charts
- Camera preview works
- Motion detection stream works
- Motion events are saved to SQLite
- Alerts are generated from motion and sensor rules

Paused:

- Fan automation is paused because the first fan driver module was likely damaged during testing.
- Raspberry Pi deployment is planned after the Mac prototype is stable.

## Architecture

```text
BME280 + BH1750
      ↓ I2C
STM32 Nucleo-F103RB
      ↓ USB Serial JSON
Python Serial Collector
      ↓
SQLite Database
      ↓
FastAPI Backend
      ↓
React Dashboard

Camera
      ↓
OpenCV Stream
      ↓
Motion Detection
      ↓
Motion Events + Alerts
      ↓
React Dashboard