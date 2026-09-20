Link to website:-  http://localhost:8501/
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
import uvicorn

# Import optimization functions from backend.py
from backend import (
    optimize_warehouses,
    calculate_cost,
    calculate_original_cost
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Warehouse Location Optimization API",
    description="Middleware connecting the Streamlit frontend with the Python optimization backend.",
    version="1.0.0"
)


# ============================================================
# DATA MODELS
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

    neighborhoods: List[Neighborhood]

    number_of_warehouses: int = Field(
        ge=1
    )

    cost_per_km: float = Field(
        ge=0
    )

    warehouse_capacity: Optional[float] = Field(
        default=None,
        ge=0
    )

    max_radius: Optional[float] = Field(
        default=None,
        ge=0
    )


# ============================================================
# HOME / HEALTH CHECK
# ============================================================

@app.get("/")
def home():

    return {
        "success": True,
        "message": "Warehouse Optimization API is running",
        "service": "Warehouse Location Optimization",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():

    return {
        "success": True,
        "status": "healthy"
    }


# ============================================================
# OPTIMIZATION ENDPOINT
# ============================================================

@app.post("/optimize")
def optimize(request: OptimizationRequest):

    try:

        # ----------------------------------------------------
        # 1. Convert incoming JSON into Python data
        # ----------------------------------------------------

        neighborhood_data = []

        for item in request.neighborhoods:

            neighborhood_data.append(
                {
                    "neighborhood":
                        item.neighborhood,

                    "latitude":
                        item.latitude,

                    "longitude":
                        item.longitude,

                    "daily_orders":
                        item.daily_orders
                }
            )


        # ----------------------------------------------------
        # 2. Convert data to DataFrame
        # ----------------------------------------------------

        df = pd.DataFrame(
            neighborhood_data
        )


        # ----------------------------------------------------
        # 3. Basic validation
        # ----------------------------------------------------

        if df.empty:

            raise HTTPException(
                status_code=400,
                detail="No neighborhood data was provided."
            )


        if request.number_of_warehouses > len(df):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Number of warehouses cannot be "
                    "greater than number of neighborhoods."
                )
            )


        if df["daily_orders"].sum() <= 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Total daily orders must be "
                    "greater than zero."
                )
            )


        # ----------------------------------------------------
        # 4. Prepare constraints
        # ----------------------------------------------------

        capacity = (
            request.warehouse_capacity
            if request.warehouse_capacity
            and request.warehouse_capacity > 0
            else None
        )


        radius = (
            request.max_radius
            if request.max_radius
            and request.max_radius > 0
            else None
        )


        # ----------------------------------------------------
        # 5. CALL BACKEND OPTIMIZATION
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
        # 6. Calculate optimized delivery cost
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
        # 7. Calculate original arrangement
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
        # 8. Calculate improvement
        # ----------------------------------------------------

        if original_distance > 0:

            distance_improvement = (

                (
                    original_distance
                    - total_distance
                )
                / original_distance

            ) * 100

        else:

            distance_improvement = 0


        if original_cost > 0:

            cost_improvement = (

                (
                    original_cost
                    - total_cost
                )
                / original_cost

            ) * 100

        else:

            cost_improvement = 0


        # ----------------------------------------------------
        # 9. Prepare warehouse response
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
        # 10. Prepare neighborhood assignments
        # ----------------------------------------------------

        assignments = []

        for _, row in result.iterrows():

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
        # 11. Warehouse utilization
        # ----------------------------------------------------

        utilization = []

        for warehouse_id in range(
            1,
            request.number_of_warehouses + 1
        ):

            warehouse_orders = result[
                result["warehouse"]
                == warehouse_id
            ]["daily_orders"].sum()


            if capacity:

                utilization_percent = (
                    warehouse_orders
                    / capacity
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
                        float(
                            capacity
                        )
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
        # 12. Final JSON response
        # ----------------------------------------------------

        response = {

            "success": True,

            "message":
                "Warehouse optimization completed successfully.",


            # ------------------------------------------------
            # Warehouse locations
            # ------------------------------------------------

            "warehouses":
                warehouses,


            # ------------------------------------------------
            # Neighborhood assignments
            # ------------------------------------------------

            "assignments":
                assignments,


            # ------------------------------------------------
            # Warehouse utilization
            # ------------------------------------------------

            "warehouse_utilization":
                utilization,


            # ------------------------------------------------
            # Optimization metrics
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Original warehouse baseline
            # ------------------------------------------------

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


        # ----------------------------------------------------
        # 13. Send response back to frontend
        # ----------------------------------------------------

        return response


    # ========================================================
    # HTTP ERROR
    # ========================================================

    except HTTPException:

        raise


    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=(
                "Internal optimization error: "
                + str(error)
            )
        )


# ============================================================
# RUN MIDDLEWARE SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print(
        "WAREHOUSE OPTIMIZATION MIDDLEWARE"
    )
    print("=" * 60)
    print(
        "Server: http://127.0.0.1:8000"
    )
    print(
        "API Docs: http://127.0.0.1:8000/docs"
    )
    print(
        "Optimization Endpoint:"
    )
    print(
        "POST http://127.0.0.1:8000/optimize"
    )
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True
    )
