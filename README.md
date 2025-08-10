# UltraSync Integration for Home Assistant

[![Paypal](https://img.shields.io/badge/paypal-donate-green.svg)](https://paypal.me/lead2gold)
[![Follow](https://img.shields.io/twitter/follow/l2gnux)](https://twitter.com/l2gnux/)<br>
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/caronc/ha-ultrasync/blob/main/hacs.json)<br>
[![Project Maintenance](https://img.shields.io/badge/maintainer-%40caronc-blue)](https://github.com/caronc)

![ZeroWire Hub Image](https://raw.githubusercontent.com/caronc/ultrasync/master/static/zerowire_hub.jpeg)

Interlogix ZeroWire and Hills ComNav (NX-595E) UltraSync Security Panel for Integration for Home Assistant Community Store (HACS)

This is based on a [a Pull Request I created here](https://github.com/home-assistant/core/pull/42549) to implement [my version of a UltraSync security panel](https://github.com/caronc/ultrasync) into Home Assistant (HA).

Unfortunately it's taking a little bit of time to get merged due to the significant backlog the HA team already has to deal with. The request comes from [a thread within the HA Community Forum](https://community.home-assistant.io/t/interlogix-ultrasync/51464) asking for it's support.

This repository simply prepares a custom component that one can use early while we wait.  The other advantage of this repository is that new things can be tried and tested before they are merged into Home Assistant.

## Installation

You can only be logged into the ComNav/ZeroWire hub with the same user *once*; a subsequent login with the same user logs out the other. Since this tool/software actively polls and maintains a login session to your Hub, it can prevent you from being able to log into at the same time elsewhere (via it's website).  **It is strongly recommended that you create a second user account on your Hub dedicated to just this service.**

### From HACS

1. Install HACS if you haven't already (see [installation guide](https://hacs.netlify.com/docs/installation/manual)).
1. Find and install **UltraSync** integration in HACS's "Integrations" tab.
1. Restart your Home Assistant.
1. Add "UltraSync" integration in Home Assistant's "**Configuration** -> **Integrations** tab.

### Manual

1. Download and unzip the [repo archive](https://github.com/caronc/ha-ultrasync/archive/master.zip). (You could also click "Download ZIP" after pressing the green button in the repo, alternatively, you could clone the repo from SSH add-on).
2. Copy contents of the archive/repo into your `/config` directory.
3. Restart your Home Assistant.
4. Add "UltraSync" integration in Home Assistant's "**Configuration** -> **Integrations** tab.

## Configuration

Go to the integrations page in your configuration and click on new **Integration** -> **UltraSync**.

**Note**: You can only be logged into the ZeroWire/UltraSync hub with the same user once; a subsequent login with the same user logs out the other. Since Home Assistant (HA) actively polls and maintains a login session to this Hub, it can prevent you from being able to log into at the same time elsewhere (via it's website). It is strongly recommended that you create a second user account on your Hub dedicated for just HA.

### Sensor

Sensors are dynamically generated on the fly.

Sensors follow the following naming convention: `{ultrasync_integration}_{sensor}`.  The `{ultrasync_integration}` refers to the name you called your integration when you set it up (the default is `Ultrasync` so it is referenced in it's slug form `ultrasync`):

- `ultrasync_area1state`: The Area 1 State
- `ultrasync_area2state`: The Area 2 State
- `ultrasync_areaXstate`: The Area X State

Zone sensors work the same way and only load what is detected:

- `ultrasync_zone1state`: The Zone 1 State
- `ultrasync_zone2state`: The Zone 2 State
- `ultrasync_zoneXstate`: The Zone X State

Output and history sensors also work the same way and only load what is detected:

- `ultrasync_output1state`: The Output 1 State
- `ultrasync_output2state`: The Output 2 State
- `ultrasync_outputXstate`: The Output X State
- `ultrasync_historyXstate`: The History State

The attributes read from the hub are associated with each Detected Zone, Area, History (by area) and Output; so you can rename them to something more appropriate if you feel the need.

There are several states each Zone and Area sensor can be at, but usually they will be one of the following: `Unknown`, `Ready`, `Not Ready`, `Armed Stay`, and `Armed Away`.  The `Unknown` state is assigned to sensors that are not reporting; they usually sit in the spots of the Areas you're not monitoring.

The state of Output sensors will ALWAYS remain `0` whether it has been turned on or off. This is normal, the Output sensor simply acts as an entity to activate the `switch` service.

The state of History sensors will be updated whenever the Area sensor changes, so generally will be either one of `Turn off` or `Turn on`.

### Event Automation

When an Zone or Sensor changes it's state an event usable for automation is triggered on the Home Assistant Bus.

Possible events are:

- `ultrasync_sensor_update`: The event includes the sensor no, name, and new status it changed to.
- `ultrasync_area_update`: The event includes the area no, name, and new status it changed to (if it did).

**Note**: Areas are sent periodic heartbeats with Interlogix devices in which case the state will not change at all.

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
- `medical`: Triggers the Alarm (Medical Alarm)
- `fire`: Triggers the Alarm (Fire Alarm)
- `panic`: Triggers the Alarm (Panic Alarm)
- `disarm`: Disarm the alarm
- `bypass`: Bypasses a specified Zone
- `switch`: Activates an Output Control entity

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
To activate the `bypass` service, simply specify the Zone entity number and call the service like so:

``` yaml
# Bypasses Zone 1
- alias: Bypass Sliding Door
  action:
    service: ultrasync.bypass
    data:
      zone: 1
```

To activate the `switch` service, simply specify the Output entity number along with the desired state for the Output (0 for off, 1 for on) like so:

``` yaml
# Activates Output 1 to the on position
- alias: Open Garage Door relay
  action:
    service: ultrasync.switch
    data:
      output: 1
      state: 1
```


## UI

A card I use that I created and works quite well can be found in this repository as well called [`ultrasync_alarm.yaml`](https://raw.githubusercontent.com/caronc/ha-ultrasync/main/ultrasync_alarm.yaml) found at the root of this GitHub repository.  It requires that you additionally have the following resources already pre-added:

- **layout-card**: [Source](https://github.com/thomasloven/lovelace-layout-card)
- **button-card**: [Source](https://github.com/custom-cards/button-card)

The `ultrasync_alarm.yaml` looks like this:
![Lovelace UltraSync Card](https://raw.githubusercontent.com/caronc/ha-ultrasync/main/ultrasync_alarm-card-preview.gif)

## Apple Homekit

If you are running Homekit in conjunction with Home Assistant via a Homekit Bridge and wish to integrate your Ultrasync panel (via this integration), you can achieve this using a combination of the Alarm Control Panel Template (Home Assistant integration) and some custom automations. This is detailed below.

### Alarm Control Panel Template

Update your Home Assistant Configuration.yaml file to include the below:

``` yaml
#Alarm Config to Allow Homekit Integration
alarm_control_panel:
  - platform: manual
    name: ultrasync_alarm_ghost
    code_arm_required: false
    arming_time: 0
    delay_time: 0
    trigger_time: 300
    disarmed:
      trigger_time: 0
    armed_away:
      arming_time: 30
      delay_time: 20
    armed_home:
      arming_time: 15
      delay_time: 10
  - platform: template
    panels:
      ultrasync_alarm:
        value_template: "{{ states('alarm_control_panel.ultrasync_alarm_ghost') }}"
        code_arm_required: false
        arm_away:
          service: alarm_control_panel.alarm_arm_away
          target:
            entity_id: alarm_control_panel.ultrasync_alarm_ghost
        arm_home:
          service: alarm_control_panel.alarm_arm_home
          target:
            entity_id: alarm_control_panel.ultrasync_alarm_ghost
        disarm:
          service: alarm_control_panel.alarm_disarm
          target:
            entity_id: alarm_control_panel.ultrasync_alarm_ghost
```

### Automations

Create the following six automations to handle arming/disarming the panel from the Home app, as well as to ensure the status of the panel is consistent in the app when it is armed/disarmed from elsewhere.

``` yaml
alias: Alarm - Disarm
description: Used by HomeKit Alarm Integration
trigger:
  - platform: state
    entity_id:
      - alarm_control_panel.ultrasync_alarm_ghost
    to: disarmed
condition: []
action:
  - service: ultrasync.disarm
    data: {}
mode: single

alias: Alarm Arming - Away
description: Used by HomeKit Alarm Integration
trigger:
  - platform: state
    entity_id:
      - alarm_control_panel.ultrasync_alarm_ghost
    to: armed_away
condition: []
action:
  - service: ultrasync.away
    data: {}
mode: single

alias: Alarm Arming - Stay
description: Used by HomeKit Alarm Integration
trigger:
  - platform: state
    entity_id:
      - alarm_control_panel.ultrasync_alarm_ghost
    to: armed_home
condition: []
action:
  - service: ultrasync.stay
    data: {}
mode: single

alias: Updates HomeKit Alarm Status to Armed - Away
description: Used by HomeKit Alarm Integration
trigger:
  - platform: state
    entity_id:
      - sensor.ultrasync_area1state
    from: null
    to: Armed Away
condition: []
action:
  - service: alarm_control_panel.alarm_arm_away
    metadata: {}
    data: {}
    target:
      entity_id: alarm_control_panel.ultrasync_alarm_ghost
mode: single

alias: Updates HomeKit Alarm Status to Armed - Stay
description: Used by HomeKit Alarm Integration
trigger:
  - platform: state
    entity_id:
      - sensor.ultrasync_area1state
    from: null
    to: Armed Stay
condition: []
action:
  - service: alarm_control_panel.alarm_arm_home
    target:
      entity_id:
        - alarm_control_panel.ultrasync_alarm_ghost
    data: {}
mode: single

alias: Updates HomeKit Alarm Status to Disarmed
description: Used by HomeKit Alarm Integration
trigger:
  - platform: state
    entity_id:
      - sensor.ultrasync_area1state
    to: Ready
    from:
      - Sensor Bypass
      - Armed Away
condition: []
action:
  - service: alarm_control_panel.alarm_disarm
    target:
      entity_id:
        - alarm_control_panel.ultrasync_alarm_ghost
    data: {}
mode: single
```

## Donations

This software is 100% open source, however [buying me a coffee](https://paypal.me/lead2gold?locale.x=en_US) shows your appreciation and greatly inspires me to continue improving the application. :)
