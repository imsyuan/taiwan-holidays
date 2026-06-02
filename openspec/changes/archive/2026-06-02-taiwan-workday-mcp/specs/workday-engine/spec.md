## ADDED Requirements

### Requirement: Workday determination from calendar data

The engine SHALL determine whether a given date is a workday using the `isHoliday` field of the loaded `data/<year>.json` calendar. A date with `isHoliday=true` SHALL be treated as a non-working day. A date with `isHoliday=false` SHALL be treated as a workday, including makeup workdays (weekend days that require working). The engine SHALL be a pure function module and MUST NOT perform any network or file I/O itself; calendar data SHALL be passed in by the caller.

#### Scenario: Regular weekday is a workday

- **WHEN** a date whose entry has `isHoliday=false` is evaluated
- **THEN** the engine reports it as a workday

#### Scenario: National holiday is not a workday

- **WHEN** a date whose entry has `isHoliday=true` is evaluated
- **THEN** the engine reports it as a non-working day

#### Scenario: Makeup workday counts as a workday

- **WHEN** a Saturday marked as a makeup workday (`isHoliday=false`, description matching 補班/補行上班/調整上班) is evaluated
- **THEN** the engine reports it as a workday

### Requirement: Count workdays in a date range

The engine SHALL count the working days, holidays, and makeup workdays within an inclusive date range `[start, end]`. Makeup workdays SHALL be counted within the workday total and SHALL also be reported separately.

#### Scenario: Count across a range containing a makeup workday

- **WHEN** the caller requests the workday count for an inclusive range
- **THEN** the engine returns the number of workdays, holidays, and makeup workdays in that range

##### Example: range spanning a holiday and a makeup workday

- **GIVEN** a 7-day range containing 5 ordinary weekdays, 1 national holiday, and 1 Saturday makeup workday
- **WHEN** the workday count is requested
- **THEN** workdays = 6, holidays = 1, makeupWorkdays = 1

### Requirement: Add workdays to a date

The engine SHALL compute the date that is N workdays from a given date. A positive N SHALL advance forward and a negative N SHALL move backward. The starting date itself SHALL NOT be counted; the result is the Nth workday after (or before) the start date.

#### Scenario: Add workdays skipping holidays and weekends

- **WHEN** the caller requests the date N workdays from a start date
- **THEN** the engine returns the date reached after skipping all non-working days

##### Example: add workdays across a weekend

- **GIVEN** start date Friday, with the following Saturday and Sunday non-working
- **WHEN** 1 workday is added
- **THEN** the result is the following Monday

### Requirement: Identify makeup workdays

The engine SHALL identify makeup workdays — days marked `isHoliday=false` whose description matches the makeup patterns (調整上班/補行上班/補班). It SHALL return the next makeup workday on or after a given base date, and SHALL return all makeup workdays within a given range when a range is provided.

#### Scenario: Find the next makeup workday

- **WHEN** the caller provides a base date
- **THEN** the engine returns the earliest makeup workday on or after that date, or null when none exists in the loaded data

#### Scenario: List makeup workdays in a range

- **WHEN** the caller provides an inclusive range
- **THEN** the engine returns all makeup workdays within that range in ascending date order

### Requirement: Optimize annual leave

The engine SHALL compute leave plans that maximize consecutive days off per annual-leave day spent, given a number of available annual-leave days and an optional date range. Each plan SHALL report the leave dates to request, the resulting continuous off range, the total days off, the leave days spent, and an efficiency value equal to total days off divided by leave days spent. Plans SHALL be returned sorted by efficiency in descending order.

#### Scenario: Bridge leave around a long holiday

- **WHEN** the caller requests leave optimization with a number of available leave days
- **THEN** the engine returns plans sorted by efficiency, each describing which dates to take off and how many continuous days off result

##### Example: one leave day bridging a holiday to a weekend

- **GIVEN** a national holiday on a Thursday followed by a normal Friday and a weekend, with 1 annual-leave day available
- **WHEN** leave optimization is requested
- **THEN** a plan taking Friday off yields a 4-day continuous break (Thu–Sun) with efficiency 4.0

### Requirement: Find travel windows

The engine SHALL compute candidate travel windows based on continuous-off runs and leave optimization, given available annual-leave days and a minimum trip length. Each window SHALL report the trip date range, the trip length, the leave dates to request, and the leave days spent. The engine SHALL NOT incorporate any flight, hotel, or attraction data. Windows SHALL be sorted by trip length divided by leave days spent in descending order.

#### Scenario: Suggest travel windows meeting a minimum length

- **WHEN** the caller requests travel windows with available leave days and a minimum trip length
- **THEN** the engine returns only windows whose trip length is at least the minimum, sorted by leave efficiency

### Requirement: Reject unavailable years and invalid input

The engine SHALL signal a structured error when calendar data for a requested year is not provided, and when input dates are malformed or a range has start later than end. It MUST NOT throw unhandled exceptions for these conditions.

#### Scenario: Requested year data is missing

- **WHEN** an operation is requested for a year whose calendar data was not supplied
- **THEN** the engine returns a structured error indicating the year is unavailable and which years are available

#### Scenario: Malformed date or inverted range

- **WHEN** a date is not in `YYYY-MM-DD` form, or a range has start after end
- **THEN** the engine returns a structured invalid-input error with a detail message
