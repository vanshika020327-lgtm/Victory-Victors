import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


EARTH_RADIUS_KM = 6371.0088


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate geographical distance between two points in kilometers.
    """

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(a))


def geometric_median(points, weights, iterations=100):
    """
    Weighted geometric median using the Weiszfeld algorithm.
    """

    points = np.asarray(points, dtype=float)
    weights = np.asarray(weights, dtype=float)

    if len(points) == 1:
        return points[0]

    if weights.sum() == 0:
        weights = np.ones(len(points))

    current = np.average(
        points,
        axis=0,
        weights=weights
    )

    for _ in range(iterations):

        distances = np.linalg.norm(
            points - current,
            axis=1
        )

        distances = np.maximum(
            distances,
            1e-10
        )

        factors = weights / distances

        new_point = (
            np.sum(
                points * factors[:, None],
                axis=0
            )
            / factors.sum()
        )

        if np.linalg.norm(
            new_point - current
        ) < 1e-7:

            break

        current = new_point

    return current


def validate_data(df):
    """
    Validate neighborhood data.
    """

    required_columns = [
        "neighborhood",
        "latitude",
        "longitude",
        "daily_orders"
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing columns: "
            + ", ".join(missing)
        )

    if df.empty:
        raise ValueError(
            "Dataset is empty."
        )

    for column in [
        "latitude",
        "longitude",
        "daily_orders"
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    if df[
        [
            "latitude",
            "longitude",
            "daily_orders"
        ]
    ].isnull().any().any():

        raise ValueError(
            "Latitude, longitude and daily_orders "
            "must contain valid numbers."
        )

    if not df["latitude"].between(
        -90, 90
    ).all():

        raise ValueError(
            "Latitude must be between -90 and 90."
        )

    if not df["longitude"].between(
        -180, 180
    ).all():

        raise ValueError(
            "Longitude must be between -180 and 180."
        )

    if (
        df["daily_orders"] < 0
    ).any():

        raise ValueError(
            "Daily orders cannot be negative."
        )

    if (
        df["daily_orders"].sum() <= 0
    ):

        raise ValueError(
            "Total daily orders must be greater than zero."
        )

    return df


def optimize_warehouses(
    df,
    number_of_warehouses,
    warehouse_capacity=None,
    max_radius=None
):
    """
    Main warehouse optimization algorithm.

    Uses demand-weighted K-Means to obtain initial warehouse
    locations, followed by weighted geometric median refinement.
    """

    df = validate_data(
        df.copy()
    )

    if number_of_warehouses < 1:

        raise ValueError(
            "At least one warehouse is required."
        )

    if number_of_warehouses > len(df):

        raise ValueError(
            "Number of warehouses cannot exceed "
            "number of neighborhoods."
        )

    coordinates = df[
        [
            "latitude",
            "longitude"
        ]
    ].values

    demand = df[
        "daily_orders"
    ].values

    # ---------------------------------------------------------
    # Step 1: Demand-weighted K-Means
    # ---------------------------------------------------------

    kmeans = KMeans(
        n_clusters=number_of_warehouses,
        random_state=42,
        n_init=20,
        max_iter=500
    )

    kmeans.fit(
        coordinates,
        sample_weight=demand
    )

    assignments = kmeans.labels_

    warehouse_locations = []

    # ---------------------------------------------------------
    # Step 2: Weighted geometric median
    # ---------------------------------------------------------

    for warehouse_id in range(
        number_of_warehouses
    ):

        indexes = np.where(
            assignments == warehouse_id
        )[0]

        if len(indexes) == 0:

            warehouse_locations.append(
                coordinates[
                    np.argmax(demand)
                ]
            )

        else:

            location = geometric_median(
                coordinates[indexes],
                demand[indexes]
            )

            warehouse_locations.append(
                location
            )

    warehouse_locations = np.array(
        warehouse_locations
    )

    # ---------------------------------------------------------
    # Step 3: Calculate distances
    # ---------------------------------------------------------

    distance_matrix = np.zeros(
        (
            len(df),
            number_of_warehouses
        )
    )

    for i in range(len(df)):

        for j in range(
            number_of_warehouses
        ):

            distance_matrix[i, j] = (
                haversine_distance(
                    df.iloc[i]["latitude"],
                    df.iloc[i]["longitude"],
                    warehouse_locations[j][0],
                    warehouse_locations[j][1]
                )
            )

    # ---------------------------------------------------------
    # Step 4: Assignment
    # ---------------------------------------------------------

    final_assignments = np.full(
        len(df),
        -1,
        dtype=int
    )

    capacity_used = np.zeros(
        number_of_warehouses
    )

    # High-demand neighborhoods first
    order = np.argsort(
        -demand
    )

    for i in order:

        candidates = []

        for warehouse_id in range(
            number_of_warehouses
        ):

            distance = (
                distance_matrix[
                    i,
                    warehouse_id
                ]
            )

            # Radius constraint
            radius_ok = (
                max_radius is None
                or max_radius <= 0
                or distance <= max_radius
            )

            # Capacity constraint
            capacity_ok = (
                warehouse_capacity is None
                or warehouse_capacity <= 0
                or (
                    capacity_used[
                        warehouse_id
                    ]
                    + demand[i]
                    <= warehouse_capacity
                )
            )

            if radius_ok and capacity_ok:

                candidates.append(
                    warehouse_id
                )

        if candidates:

            best = min(
                candidates,
                key=lambda x:
                distance_matrix[
                    i,
                    x
                ]
            )

            final_assignments[i] = best

            capacity_used[
                best
            ] += demand[i]

        else:

            # If constraints make assignment impossible,
            # assign to the nearest warehouse.
            final_assignments[i] = np.argmin(
                distance_matrix[i]
            )

    # ---------------------------------------------------------
    # Step 5: Final distance
    # ---------------------------------------------------------

    final_distances = np.array(
        [
            distance_matrix[
                i,
                final_assignments[i]
            ]
            for i in range(len(df))
        ]
    )

    # ---------------------------------------------------------
    # Step 6: Results
    # ---------------------------------------------------------

    result = df.copy()

    result[
        "warehouse"
    ] = final_assignments + 1

    result[
        "distance_km"
    ] = final_distances

    result[
        "weighted_distance"
    ] = (
        result["daily_orders"]
        * result["distance_km"]
    )

    return (
        result,
        warehouse_locations,
        distance_matrix
    )


def calculate_cost(
    result,
    cost_per_km
):
    """
    Calculate total delivery cost.
    """

    result = result.copy()

    result[
        "delivery_cost"
    ] = (
        result["weighted_distance"]
        * cost_per_km
    )

    total_distance = (
        result["weighted_distance"].sum()
    )

    total_cost = (
        result["delivery_cost"].sum()
    )

    total_orders = (
        result["daily_orders"].sum()
    )

    average_distance = (
        total_distance / total_orders
        if total_orders > 0
        else 0
    )

    return (
        result,
        total_distance,
        total_cost,
        average_distance
    )


def calculate_original_cost(
    df,
    cost_per_km
):
    """
    Calculate baseline cost using one central,
    demand-weighted warehouse.
    """

    latitude = np.average(
        df["latitude"],
        weights=df["daily_orders"]
    )

    longitude = np.average(
        df["longitude"],
        weights=df["daily_orders"]
    )

    distances = haversine_distance(
        df["latitude"].values,
        df["longitude"].values,
        latitude,
        longitude
    )

    weighted_distance = (
        distances
        * df["daily_orders"].values
    ).sum()

    cost = (
        weighted_distance
        * cost_per_km
    )

    return (
        latitude,
        longitude,
        weighted_distance,
        cost
    )
