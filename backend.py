import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


EARTH_RADIUS_KM = 6371.0088


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Calculate geographical distance between two points.
    Result is in kilometers.
    """

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)

    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        +
        np.cos(lat1)
        *
        np.cos(lat2)
        *
        np.sin(dlon / 2) ** 2
    )

    a = np.clip(a, 0, 1)

    return (
        EARTH_RADIUS_KM
        *
        2
        *
        np.arcsin(
            np.sqrt(a)
        )
    )


# ============================================================
# DATA VALIDATION
# ============================================================

def validate_data(df):

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
            "Missing required columns: "
            + ", ".join(missing)
        )

    if df.empty:

        raise ValueError(
            "The dataset is empty."
        )

    df = df.copy()

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    df["daily_orders"] = pd.to_numeric(
        df["daily_orders"],
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
        -90,
        90
    ).all():

        raise ValueError(
            "Latitude must be between -90 and 90."
        )

    if not df["longitude"].between(
        -180,
        180
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

    if (
        df["neighborhood"]
        .astype(str)
        .str.strip()
        .eq("")
        .any()
    ):

        raise ValueError(
            "Neighborhood names cannot be empty."
        )

    return df


# ============================================================
# WEIGHTED GEOMETRIC MEDIAN
# ============================================================

def geometric_median(
    points,
    weights,
    iterations=100
):
    """
    Calculate weighted geometric median
    using the Weiszfeld algorithm.
    """

    points = np.asarray(
        points,
        dtype=float
    )

    weights = np.asarray(
        weights,
        dtype=float
    )

    if len(points) == 1:

        return points[0]

    if weights.sum() <= 0:

        weights = np.ones(
            len(points)
        )

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

        factors = (
            weights / distances
        )

        new_point = (
            np.sum(
                points
                *
                factors[:, None],
                axis=0
            )
            /
            factors.sum()
        )

        movement = np.linalg.norm(
            new_point - current
        )

        current = new_point

        if movement < 1e-7:

            break

    return current


# ============================================================
# WAREHOUSE OPTIMIZATION
# ============================================================

def optimize_warehouses(
    df,
    number_of_warehouses,
    warehouse_capacity=None,
    max_radius=None
):
    """
    Optimize warehouse locations.

    Steps:
    1. Demand-weighted K-Means.
    2. Weighted geometric median refinement.
    3. Calculate distances.
    4. Assign neighborhoods.
    5. Apply capacity and radius constraints.
    """

    df = validate_data(df)

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
    ].to_numpy()

    demand = df[
        "daily_orders"
    ].to_numpy()

    # --------------------------------------------------------
    # STEP 1: K-MEANS
    # --------------------------------------------------------

    model = KMeans(
        n_clusters=number_of_warehouses,
        random_state=42,
        n_init=20,
        max_iter=500
    )

    model.fit(
        coordinates,
        sample_weight=demand
    )

    assignments = model.labels_

    # --------------------------------------------------------
    # STEP 2: GEOMETRIC MEDIAN
    # --------------------------------------------------------

    warehouse_locations = []

    for warehouse_id in range(
        number_of_warehouses
    ):

        indexes = np.where(
            assignments == warehouse_id
        )[0]

        if len(indexes) == 0:

            index = np.argmax(
                demand
            )

            warehouse_locations.append(
                coordinates[index]
            )

        else:

            location = geometric_median(
                coordinates[indexes],
                demand[indexes]
            )

            warehouse_locations.append(
                location
            )

    warehouse_locations = np.asarray(
        warehouse_locations
    )

    # --------------------------------------------------------
    # STEP 3: DISTANCE MATRIX
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # STEP 4: ASSIGNMENT
    # --------------------------------------------------------

    final_assignments = np.full(
        len(df),
        -1,
        dtype=int
    )

    capacity_used = np.zeros(
        number_of_warehouses
    )

    # High-demand locations first.
    processing_order = np.argsort(
        -demand
    )

    for i in processing_order:

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
                or
                (
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
                key=lambda warehouse_id:
                    distance_matrix[
                        i,
                        warehouse_id
                    ]
            )

            final_assignments[i] = best

            capacity_used[
                best
            ] += demand[i]

        else:

            # Fallback if constraints make assignment impossible.
            final_assignments[i] = np.argmin(
                distance_matrix[i]
            )

    # --------------------------------------------------------
    # STEP 5: FINAL DISTANCES
    # --------------------------------------------------------

    final_distances = np.array(
        [
            distance_matrix[
                i,
                final_assignments[i]
            ]

            for i in range(len(df))
        ]
    )

    # --------------------------------------------------------
    # STEP 6: CREATE RESULT
    # --------------------------------------------------------

    result = df.copy()

    result["warehouse"] = (
        final_assignments + 1
    )

    result["distance_km"] = (
        final_distances
    )

    result["weighted_distance"] = (
        result["daily_orders"]
        *
        result["distance_km"]
    )

    return (
        result,
        warehouse_locations,
        distance_matrix
    )


# ============================================================
# COST CALCULATION
# ============================================================

def calculate_cost(
    result,
    cost_per_km
):

    result = result.copy()

    result["delivery_cost"] = (
        result["weighted_distance"]
        *
        cost_per_km
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

    if total_orders > 0:

        average_distance = (
            total_distance
            /
            total_orders
        )

    else:

        average_distance = 0

    return (
        result,
        total_distance,
        total_cost,
        average_distance
    )


# ============================================================
# ORIGINAL BASELINE
# ============================================================

def calculate_original_cost(
    df,
    cost_per_km
):
    """
    Baseline:
    one demand-weighted central warehouse.
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
        df["latitude"].to_numpy(),
        df["longitude"].to_numpy(),
        latitude,
        longitude
    )

    weighted_distance = (
        distances
        *
        df["daily_orders"].to_numpy()
    ).sum()

    cost = (
        weighted_distance
        *
        cost_per_km
    )

    return (
        latitude,
        longitude,
        weighted_distance,
        cost
    )
