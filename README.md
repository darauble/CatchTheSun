# CatchTheSun

This is a small Python 3 utility for finding a location behind the object, which one wants to photograph in the background of the Sun. Utility provides a map to put a pin of the observer and the object. The azimuth and distance (in kilometers) is counted automatically. The date interval is used to search when the nearest sunrise or sunset would get behind the object from the observer's point.

The utility calculates the time of exact sunrise or sunset. Note that it takes additional time for the full Sun's disk to appear, so the location might not be exact: leave some space to move. Also, some objects might be significantly above the horizon even in flat locations. But in general it would help to find the required spot, give or take few (tens of) meters.

## Dependencies

This utility requires Folium, NumPy, Qt5 and SkyField libraries. Install them either via pip or using OS distribution system if available.

When the utility is run for the first time, its window does not appear immediatelly. It is because it needs to download sky objects database (~16 MB). Later it starts instantly.
