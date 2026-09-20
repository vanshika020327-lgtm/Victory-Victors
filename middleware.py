
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

import pandas as pd
import uvicorn

from backend import (
    optimize_warehouses,
    calculate_cost,
    calculate_original_cost
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Warehouse Optimization API",
    description="Middleware between Streamlit frontend and optimization backend.",
    version="1.0.0"
)


# ============================================================
# REQUEST DATA MODELS
# ============================================================

class Neighborhood(BaseModel):

    neighborhood: str

    latitude: float = Field(
        ge=-90,
        le=90
    )

    longitude: float = Field(
        ge=-180,
        le=180
    )

    daily_orders: float = Field(
        ge=0
    )


class OptimizationRequest(BaseModel):

    neighborhoods: List[
        Neighborhood
    ]

    number_of_warehouses: int = Field(
        ge=1
    )

    cost_per_km: float = Field(
        ge=0
    )

    warehouse_capacity: Optional[
        float
    ] = Field(
        default=None,
        ge=0
    )

    max_radius: Optional[
        float
    ] = Field(
        default=None,
        ge=0
    )


# ============================================================
# HOME ENDPOINT
# ============================================================

@app.get("/")
def home():

    return {
        "success": True,
        "message":
            "Warehouse Optimization API is running",
        "version":
            "1.0.0"
    }


# ============================================================
# HEALTH ENDPOINT
# ============================================================

@app.get("/health")
def health():

    return {
        "success": True,
        "status": "healthy"
    }


# ============================================================
# OPTIMIZATION ENDPOINT
# ============================================================

@app.post("/optimize")
def optimize(
    request: OptimizationRequest
):

    try:

        # ----------------------------------------------------
        # Convert request to DataFrame
        # ----------------------------------------------------

        data = []

        for neighborhood in (
            request.neighborhoods
        ):

            data.append(
                {
                    "neighborhood":
                        neighborhood.neighborhood,

                    "latitude":
                        neighborhood.latitude,

                    "longitude":
                        neighborhood.longitude,

                    "daily_orders":
                        neighborhood.daily_orders
                }
            )


        df = pd.DataFrame(
            data
        )


        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        if df.empty:

            raise HTTPException(
                status_code=400,
                detail=
                    "No neighborhood data provided."
            )


        if (
            request.number_of_warehouses
            >
            len(df)
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Number of warehouses cannot "
                    "exceed number of neighborhoods."
                )
            )


        # ----------------------------------------------------
        # Convert zero constraints to None
        # ----------------------------------------------------

        capacity = (
            request.warehouse_capacity
            if (
                request.warehouse_capacity
                and
                request.warehouse_capacity > 0
            )
            else None
        )


        radius = (
            request.max_radius
            if (
                request.max_radius
                and
                request.max_radius > 0
            )
            else None
        )


        # ----------------------------------------------------
        # CALL BACKEND
        # ----------------------------------------------------

        (
            result,
            warehouse_locations,
            distance_matrix
        ) = optimize_warehouses(

            df,

            request.number_of_warehouses,

            capacity,

            radius
        )


        # ----------------------------------------------------
        # COST
        # ----------------------------------------------------

        (
            result,
            total_distance,
            total_cost,
            average_distance
        ) = calculate_cost(

            result,

            request.cost_per_km
        )


        # ----------------------------------------------------
        # ORIGINAL BASELINE
        # ----------------------------------------------------

        (
            original_lat,
            original_lon,
            original_distance,
            original_cost
        ) = calculate_original_cost(

            df,

            request.cost_per_km
        )


        # ----------------------------------------------------
        # IMPROVEMENTS
        # ----------------------------------------------------

        if original_distance > 0:

            distance_improvement = (

                (
                    original_distance
                    -
                    total_distance
                )
                /
                original_distance

            ) * 100

        else:

            distance_improvement = 0


        if original_cost > 0:

            cost_improvement = (

                (
                    original_cost
                    -
                    total_cost
                )
                /
                original_cost

            ) * 100

        else:

            cost_improvement = 0


        # ----------------------------------------------------
        # WAREHOUSE DATA
        # ----------------------------------------------------

        warehouses = []

        for i, location in enumerate(
            warehouse_locations
        ):

            warehouses.append(
                {
                    "warehouse_id":
                        i + 1,

                    "latitude":
                        float(
                            location[0]
                        ),

                    "longitude":
                        float(
                            location[1]
                        )
                }
            )


        # ----------------------------------------------------
        # ASSIGNMENT DATA
        # ----------------------------------------------------

        assignments = []

        for _, row in (
            result.iterrows()
        ):

            assignments.append(
                {
                    "neighborhood":
                        str(
                            row[
                                "neighborhood"
                            ]
                        ),

                    "latitude":
                        float(
                            row[
                                "latitude"
                            ]
                        ),

                    "longitude":
                        float(
                            row[
                                "longitude"
                            ]
                        ),

                    "daily_orders":
                        float(
                            row[
                                "daily_orders"
                            ]
                        ),

                    "warehouse":
                        int(
                            row[
                                "warehouse"
                            ]
                        ),

                    "distance_km":
                        float(
                            row[
                                "distance_km"
                            ]
                        ),

                    "weighted_distance":
                        float(
                            row[
                                "weighted_distance"
                            ]
                        ),

                    "delivery_cost":
                        float(
                            row[
                                "delivery_cost"
                            ]
                        )
                }
            )


        # ----------------------------------------------------
        # WAREHOUSE UTILIZATION
        # ----------------------------------------------------

        utilization = []

        for warehouse_id in range(
            1,
            request.number_of_warehouses + 1
        ):

            warehouse_orders = (
                result[
                    result[
                        "warehouse"
                    ]
                    ==
                    warehouse_id
                ][
                    "daily_orders"
                ].sum()
            )


            if capacity:

                utilization_percent = (

                    warehouse_orders
                    /
                    capacity

                ) * 100

            else:

                utilization_percent = None


            utilization.append(
                {
                    "warehouse_id":
                        warehouse_id,

                    "daily_orders":
                        float(
                            warehouse_orders
                        ),

                    "capacity":
                        float(capacity)
                        if capacity
                        else None,

                    "utilization_percent":
                        float(
                            utilization_percent
                        )
                        if utilization_percent
                        is not None
                        else None
                }
            )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "success": True,

            "message":
                "Optimization completed successfully.",


            "warehouses":
                warehouses,


            "assignments":
                assignments,


            "warehouse_utilization":
                utilization,


            "metrics":
                {

                    "total_neighborhoods":
                        len(df),

                    "total_orders":
                        float(
                            df[
                                "daily_orders"
                            ].sum()
                        ),

                    "number_of_warehouses":
                        request.number_of_warehouses,

                    "optimized_weighted_distance":
                        float(
                            total_distance
                        ),

                    "optimized_average_distance":
                        float(
                            average_distance
                        ),

                    "optimized_delivery_cost":
                        float(
                            total_cost
                        ),

                    "original_weighted_distance":
                        float(
                            original_distance
                        ),

                    "original_delivery_cost":
                        float(
                            original_cost
                        ),

                    "distance_improvement_percent":
                        float(
                            distance_improvement
                        ),

                    "cost_improvement_percent":
                        float(
                            cost_improvement
                        )
                },


            "original_warehouse":
                {

                    "latitude":
                        float(
                            original_lat
                        ),

                    "longitude":
                        float(
                            original_lon
                        )
                }
        }


    except HTTPException:

        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print(
        "WAREHOUSE OPTIMIZATION MIDDLEWARE"
    )
    print("=" * 60)
    print(
        "API: http://127.0.0.1:8000"
    )
    print(
        "Documentation: http://127.0.0.1:8000/docs"
    )
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )
