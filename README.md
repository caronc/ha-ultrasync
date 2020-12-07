# UltraSync Integration for Home Assistant

[![hacs](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](hacs.json)

![ZeroWire Hub Image](https://raw.githubusercontent.com/caronc/ultrasync/master/static/zerowire_hub.jpeg)

Interlogix ZeroWire and Hills ComNav (NX-595E) UltraSync Security Panel for Integration for Home Assistant Community Store (HACS)

This is based on a [a Pull Request I created here](https://github.com/home-assistant/core/pull/42549) to implement [my version of a UltraSync security panel](https://github.com/caronc/ultrasync) into Home Assistant (HA).

Unfortunately it's taking a little bit of time to get merged due to the significant backlog the HA team already has to deal with. The request comes from [a thread within the HA Community Forum](https://community.home-assistant.io/t/interlogix-ultrasync/51464) asking for it's support.

This repository simply prepares a custom component that one can use early while we wait.  The other advantage of this repository is that new things can be tried and tested before they are merged into Home Assistant.

## Installation

You can only be logged into the ComNav/ZeroWire hub with the same user *once*; a subsequent login with the same user logs out the other. Since this tool/software actively polls and maintains a login session to your Hub, it can prevent you from being able to log into at the same time elsewhere (via it's website).  **It is strongly recommended that you create a second user account on your Hub dedicated to just this service.**

### From HACS

1. Install HACS if you haven't already (see [installation guide](https://hacs.netlify.com/docs/installation/manual)).
2. Add custom repository `https://github.com/caronc/ha-ultrasync` as "Integration" in the settings tab of HACS.
3. Find and install **UltraSync Beta** integration in HACS's "Integrations" tab.
4. Restart your Home Assistant.
5. Add "UltraSync Beta" integration in Home Assistant's "**Configuration** -> **Integrations** tab.

### Manual

1. Download and unzip the [repo archive](https://github.com/caronc/ha-ultrasync/archive/master.zip). (You could also click "Download ZIP" after pressing the green button in the repo, alternatively, you could clone the repo from SSH add-on).
2. Copy contents of the archive/repo into your `/config` directory.
3. Restart your Home Assistant.
4. Add "UltraSync Beta" integration in Home Assistant's "**Configuration** -> **Integrations** tab.

## Configuration

Go to the integrations page in your configuration and click on new **Integration** -> **UltraSync**.

**Note**: You can only be logged into the ZeroWire/UltraSync hub with the same user once; a subsequent login with the same user logs out the other. Since Home Assistant (HA) actively polls and maintains a login session to this Hub, it can prevent you from being able to log into at the same time elsewhere (via it's website). It is strongly recommended that you create a second user account on your Hub dedicated for just HA.

### Sensor

This component will create these sensors in the format of `{ultrasync_hubname}_{sensor}`;  The below example assumes you accept the default name of `UltraSync` (which is still represented in lowercase):
- `ultrasync_area1state`: The Area 1 State
- `ultrasync_area2state`: The Area 2 State
- `ultrasync_area3state`: The Area 3 State
- `ultrasync_area4state`: The Area 4 State

There are several states each sensor can be at, but usually they will be one of the following: `Unknown`, `Ready`, `Not Ready`, `Armed Stay`, and `Armed Away`.  The `Unknown` state is assigned to sensors that are not reporting; they usually sit in the spots of the Area's you're not monitoring.

### Event Automation

When an Zone or Sensor changes it's state an event usable for automation is triggered on the Home Assistant Bus.

Possible events are:

- `ultrasync_sensor_update`: The event includes the sensor no, name, and new status it changed to.
- `ultrasync_area_update`: The event includes the area no, name, and new status it changed to (if it did). **Note**: Area's are sent periodic heartbeats in which case the state will not change at all.

Example automation to send a message via [Apprise](https://www.home-assistant.io/integrations/apprise/) on a sensor change in your home:

```yaml
- alias: House Movement
  trigger:
    platform: event
    event_type: ultrasync_sensor_update
  action:
    service: notify.apprise
    data:
      title: "Sensor activated!"
      message: "{{trigger.event.data.name}} has new status {{trigger.event.data.status}}"
```

### Services

Available services:

- `stay`: Set alarm scene to Stay Mode
- `away`: Set alarm scene to Away Mode (fully activate Alarm)
- `disarm`: Disarm the alarm

As an example you may want to `arm` your alarm in `stay` mode each night and disarm it in the morning like so:

```yaml
# Alarm Activation
- alias: Activate Nightly Alarm
  trigger:
    platform: time
    at: "23:00:00"
  action:
    service: ultrasync.stay

# Alarm Deactivation
- alias: Disarm Nightly Alarm
  trigger:
    platform: time
    at: "06:00:00"
  action:
    service: ultrasync.disarm
```

## Lovelace UI
A card I use that created and works quite well can be found in this repository as well called `ultrasync_alarm.yaml`.  It requires that you additionally have the following resources already pre-added:

 - **layout-card**: [Source](https://github.com/thomasloven/lovelace-layout-card)
 - **button-card**: [Source](https://github.com/custom-cards/button-card)

The `ultrasync_alarm.yaml` looks like this:
![Lovelace UltraSync Card](https://raw.githubusercontent.com/caronc/ha-ultrasync/main/ultrasync_alarm-card-preview.gif)

## Donations
This software is 100% open source, however [buying me a coffee](https://paypal.me/lead2gold?locale.x=en_US) shows your appreciation and greatly inspires me to continue improving the application. :)

