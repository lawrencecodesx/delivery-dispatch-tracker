from math import asin, atan2, cos, radians, sin, sqrt

EARTH_RADIUS_METERS = 6_371_000.0


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    latitude_delta = radians(lat2 - lat1)
    longitude_delta = radians(lon2 - lon1)
    value = sin(latitude_delta / 2) ** 2 + cos(radians(lat1)) * cos(
        radians(lat2)
    ) * sin(longitude_delta / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(min(1.0, value)))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    latitude1, latitude2 = radians(lat1), radians(lat2)
    longitude_delta = radians(lon2 - lon1)
    return atan2(
        sin(longitude_delta) * cos(latitude2),
        cos(latitude1) * sin(latitude2)
        - sin(latitude1) * cos(latitude2) * cos(longitude_delta),
    )


def distance_to_route_segment_meters(
    point_lat: float,
    point_lon: float,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> float:
    segment_length = haversine_meters(start_lat, start_lon, end_lat, end_lon)
    if segment_length == 0:
        return haversine_meters(point_lat, point_lon, start_lat, start_lon)

    start_to_point = haversine_meters(start_lat, start_lon, point_lat, point_lon)
    start_to_end_bearing = _bearing(start_lat, start_lon, end_lat, end_lon)
    start_to_point_bearing = _bearing(start_lat, start_lon, point_lat, point_lon)
    angular_distance = start_to_point / EARTH_RADIUS_METERS
    cross_track_angle = asin(
        max(
            -1.0,
            min(
                1.0,
                sin(angular_distance)
                * sin(start_to_point_bearing - start_to_end_bearing),
            ),
        )
    )
    along_track = atan2(
        sin(angular_distance) * cos(start_to_point_bearing - start_to_end_bearing),
        cos(angular_distance),
    ) * EARTH_RADIUS_METERS
    if along_track < 0:
        return start_to_point
    if along_track > segment_length:
        return haversine_meters(point_lat, point_lon, end_lat, end_lon)
    return abs(cross_track_angle) * EARTH_RADIUS_METERS