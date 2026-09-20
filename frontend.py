import streamlit as st
import pandas as pd
import folium
import requests

from streamlit_folium import st_folium


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="Warehouse Optimization",
    page_icon="🏭",
    layout="wide"
)


# ============================================================
# TITLE
# ============================================================

st.title(
    "🏭 Warehouse Location Optimization Platform"
)

st.write(
    """
    Optimize warehouse locations, assign neighborhoods,
    and minimize demand-weighted delivery costs.
    """
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ Optimization Settings"
)


number_of_warehouses = (
    st.sidebar.number_input(

        "Number of Warehouses",

        min_value=1,

        max_value=20,

        value=2,

        step=1
    )
)


cost_per_km = (
    st.sidebar.number_input(

        "Delivery Cost per Order-KM",

        min_value=0.0,

        value=1.0,

        step=0.1
    )
)


warehouse_capacity = (
    st.sidebar.number_input(

        "Warehouse Capacity (orders/day)",

        min_value=0.0,

        value=0.0,

        step=100.0,

        help=
            "Enter 0 for unlimited capacity."
    )
)


max_radius = (
    st.sidebar.number_input(

        "Maximum Service Radius (km)",

        min_value=0.0,

        value=0.0,

        step=1.0,

        help=
            "Enter 0 for unlimited radius."
    )
)


# ============================================================
# SAMPLE DATA
# ============================================================

def create_sample_data():

    return pd.DataFrame(
        {

            "neighborhood": [

                "Central",

                "North",

                "South",

                "East",

                "West",

                "North-East",

                "North-West",

                "South-East",

                "South-West",

                "Airport",

                "Industrial",

                "University"
            ],


            "latitude": [

                12.9716,

                13.0358,

                12.9116,

                12.9850,

                12.9507,

                13.0150,

                13.0200,

                12.9300,

                12.9250,

                13.1986,

                13.0500,

                12.9352
            ],


            "longitude": [

                77.5946,

                77.5970,

                77.6100,

                77.6500,

                77.5300,

                77.6700,

                77.5500,

                77.6800,

                77.5400,

                77.7066,

                77.5000,

                77.6200
            ],


            "daily_orders": [

                800,

                550,

                600,

                900,

                500,

                700,

                450,

                650,

                400,

                750,

                300,

                850
            ]
        }
    )


# ============================================================
# DATA INPUT
# ============================================================

st.sidebar.header(
    "📥 Neighborhood Data"
)


data_option = st.sidebar.selectbox(

    "Data Source",

    [
        "Sample Data",

        "Upload CSV",

        "Enter Manually"
    ]
)


if data_option == "Sample Data":

    df = create_sample_data()


elif data_option == "Upload CSV":

    uploaded_file = (
        st.sidebar.file_uploader(

            "Upload CSV",

            type=["csv"]
        )
    )


    if uploaded_file is None:

        st.info(
            "Upload a CSV file from the sidebar."
        )

        st.stop()


    try:

        df = pd.read_csv(
            uploaded_file
        )

    except Exception as error:

        st.error(
            f"Unable to read CSV: {error}"
        )

        st.stop()


else:

    df = st.data_editor(

        create_sample_data(),

        num_rows="dynamic",

        use_container_width=True
    )


# ============================================================
# VALIDATION
# ============================================================

required_columns = [

    "neighborhood",

    "latitude",

    "longitude",

    "daily_orders"
]


missing_columns = [

    column

    for column in required_columns

    if column not in df.columns
]


if missing_columns:

    st.error(

        "Missing required columns: "
        +
        ", ".join(
            missing_columns
        )
    )

    st.stop()


# Convert numerical values.

try:

    df["latitude"] = pd.to_numeric(
        df["latitude"]
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"]
    )

    df["daily_orders"] = pd.to_numeric(
        df["daily_orders"]
    )

except Exception:

    st.error(
        "Latitude, longitude and daily_orders "
        "must contain numeric values."
    )

    st.stop()


if len(df) == 0:

    st.error(
        "No neighborhood data available."
    )

    st.stop()


# ============================================================
# DATA SUMMARY
# ============================================================

st.header(
    "📊 Neighborhood Data"
)


col1, col2, col3, col4 = (
    st.columns(4)
)


with col1:

    st.metric(
        "Neighborhoods",
        len(df)
    )


with col2:

    st.metric(
        "Total Daily Orders",
        f"{df['daily_orders'].sum():,.0f}"
    )


with col3:

    st.metric(
        "Average Orders",
        f"{df['daily_orders'].mean():,.0f}"
    )


with col4:

    st.metric(
        "Maximum Orders",
        f"{df['daily_orders'].max():,.0f}"
    )


st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# INITIAL MAP
# ============================================================

st.header(
    "🗺️ Neighborhood Locations"
)


center_lat = (
    df["latitude"].mean()
)


center_lon = (
    df["longitude"].mean()
)


initial_map = folium.Map(

    location=[
        center_lat,
        center_lon
    ],

    zoom_start=11
)


for _, row in df.iterrows():

    folium.CircleMarker(

        location=[
            row["latitude"],
            row["longitude"]
        ],

        radius=7,

        color="blue",

        fill=True,

        fill_color="blue",

        fill_opacity=0.8,

        popup=(
            f"<b>"
            f"{row['neighborhood']}"
            f"</b><br>"
            f"Daily Orders: "
            f"{row['daily_orders']}"
        )
    ).add_to(
        initial_map
    )


st_folium(

    initial_map,

    width=None,

    height=500
)


# ============================================================
# OPTIMIZATION
# ============================================================

st.header(
    "🚀 Run Optimization"
)


run_optimization = st.button(

    "🔍 Optimize Warehouse Locations",

    type="primary",

    use_container_width=True
)


if run_optimization:

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if (
        number_of_warehouses
        >
        len(df)
    ):

        st.error(
            "Number of warehouses cannot exceed "
            "number of neighborhoods."
        )

        st.stop()


    if (
        df["daily_orders"] < 0
    ).any():

        st.error(
            "Daily orders cannot be negative."
        )

        st.stop()


    if (
        df["daily_orders"].sum()
        <= 0
    ):

        st.error(
            "Total daily orders must be greater than zero."
        )

        st.stop()


    # --------------------------------------------------------
    # Prepare API request
    # --------------------------------------------------------

    request_data = {

        "neighborhoods":
            df[
                [
                    "neighborhood",
                    "latitude",
                    "longitude",
                    "daily_orders"
                ]
            ].to_dict(
                orient="records"
            ),


        "number_of_warehouses":
            int(
                number_of_warehouses
            ),


        "cost_per_km":
            float(
                cost_per_km
            ),


        "warehouse_capacity":
            (
                float(
                    warehouse_capacity
                )
                if warehouse_capacity > 0
                else None
            ),


        "max_radius":
            (
                float(
                    max_radius
                )
                if max_radius > 0
                else None
            )
    }


    # --------------------------------------------------------
    # Send request to middleware
    # --------------------------------------------------------

    try:

        with st.spinner(
            "Connecting to optimization server..."
        ):

            response = requests.post(

                f"{API_URL}/optimize",

                json=request_data,

                timeout=120
            )


    except requests.exceptions.ConnectionError:

        st.error(
            """
            ❌ Cannot connect to middleware.

            Make sure you started:

            `python middleware.py`
            """
        )

        st.stop()


    except requests.exceptions.Timeout:

        st.error(
            "The optimization server took too long to respond."
        )

        st.stop()


    except Exception as error:

        st.error(
            f"Connection error: {error}"
        )

        st.stop()


    # --------------------------------------------------------
    # Process API response
    # --------------------------------------------------------

    if response.status_code != 200:

        try:

            error_message = (
                response.json()
                .get(
                    "detail",
                    "Unknown server error."
                )
            )

        except Exception:

            error_message = (
                response.text
            )


        st.error(
            f"Optimization failed: {error_message}"
        )

        st.stop()


    try:

        data = response.json()

    except Exception:

        st.error(
            "Middleware returned an invalid response."
        )

        st.stop()


    # ========================================================
    # RESULTS
    # ========================================================

    st.success(
        "Optimization completed successfully!"
    )


    metrics = data[
        "metrics"
    ]


    warehouses = data[
        "warehouses"
    ]


    assignments = data[
        "assignments"
    ]


    # ========================================================
    # METRICS
    # ========================================================

    st.header(
        "📈 Optimization Results"
    )


    c1, c2, c3, c4 = (
        st.columns(4)
    )


    with c1:

        st.metric(
            "Warehouses",
            metrics[
                "number_of_warehouses"
            ]
        )


    with c2:

        st.metric(
            "Weighted Distance",
            (
                f"{metrics['optimized_weighted_distance']:.2f}"
                " order-km"
            )
        )


    with c3:

        st.metric(
            "Average Distance",
            (
                f"{metrics['optimized_average_distance']:.2f}"
                " km"
            )
        )


    with c4:

        st.metric(
            "Daily Delivery Cost",
            (
                f"{metrics['optimized_delivery_cost']:.2f}"
            )
        )


    # ========================================================
    # WAREHOUSE LOCATIONS
    # ========================================================

    st.subheader(
        "🏭 Optimized Warehouse Locations"
    )


    warehouse_df = pd.DataFrame(
        warehouses
    )


    warehouse_df.columns = [

        "Warehouse",

        "Latitude",

        "Longitude"
    ]


    st.dataframe(

        warehouse_df,

        use_container_width=True,

        hide_index=True
    )


    # ========================================================
    # OPTIMIZED MAP
    # ========================================================

    st.subheader(
        "🗺️ Optimized Map"
    )


    optimized_map = folium.Map(

        location=[
            center_lat,
            center_lon
        ],

        zoom_start=11
    )


    colors = [

        "red",

        "blue",

        "green",

        "purple",

        "orange",

        "darkred",

        "lightblue",

        "darkgreen",

        "pink",

        "cadetblue"
    ]


    # --------------------------------------------------------
    # Warehouse dictionary
    # --------------------------------------------------------

    warehouse_lookup = {

        warehouse[
            "warehouse_id"
        ]:
            warehouse

        for warehouse
        in warehouses
    }


    # --------------------------------------------------------
    # Neighborhood markers
    # --------------------------------------------------------

    for assignment in assignments:

        warehouse_id = (
            assignment[
                "warehouse"
            ]
        )


        color = colors[
            (
                warehouse_id - 1
            )
            %
            len(colors)
        ]


        folium.CircleMarker(

            location=[

                assignment[
                    "latitude"
                ],

                assignment[
                    "longitude"
                ]
            ],

            radius=7,

            color=color,

            fill=True,

            fill_color=color,

            fill_opacity=0.85,

            popup=(

                f"<b>"
                f"{assignment['neighborhood']}"
                f"</b><br>"

                f"Daily Orders: "
                f"{assignment['daily_orders']}<br>"

                f"Warehouse: "
                f"{warehouse_id}<br>"

                f"Distance: "
                f"{assignment['distance_km']:.2f}"
                f" km<br>"

                f"Delivery Cost: "
                f"{assignment['delivery_cost']:.2f}"
            )
        ).add_to(
            optimized_map
        )


        # ----------------------------------------------------
        # Assignment line
        # ----------------------------------------------------

        warehouse = (
            warehouse_lookup[
                warehouse_id
            ]
        )


        folium.PolyLine(

            locations=[

                [

                    assignment[
                        "latitude"
                    ],

                    assignment[
                        "longitude"
                    ]

                ],

                [

                    warehouse[
                        "latitude"
                    ],

                    warehouse[
                        "longitude"
                    ]

                ]

            ],

            color=color,

            weight=1.5,

            opacity=0.5

        ).add_to(
            optimized_map
        )


    # --------------------------------------------------------
    # Warehouse markers
    # --------------------------------------------------------

    for warehouse in warehouses:

        warehouse_id = (
            warehouse[
                "warehouse_id"
            ]
        )


        color = colors[
            (
                warehouse_id - 1
            )
            %
            len(colors)
        ]


        folium.Marker(

            location=[

                warehouse[
                    "latitude"
                ],

                warehouse[
                    "longitude"
                ]

            ],

            popup=(

                f"<b>"
                f"Warehouse {warehouse_id}"
                f"</b><br>"

                f"Latitude: "
                f"{warehouse['latitude']:.6f}<br>"

                f"Longitude: "
                f"{warehouse['longitude']:.6f}"
            ),

            icon=folium.Icon(

                color=color,

                icon="home",

                prefix="fa"
            )
        ).add_to(
            optimized_map
        )


    st_folium(

        optimized_map,

        width=None,

        height=600
    )


    # ========================================================
    # ASSIGNMENTS TABLE
    # ========================================================

    st.subheader(
        "📦 Neighborhood Assignments"
    )


    assignment_df = pd.DataFrame(
        assignments
    )


    assignment_df = (
        assignment_df.rename(

            columns={

                "neighborhood":
                    "Neighborhood",

                "latitude":
                    "Latitude",

                "longitude":
                    "Longitude",

                "daily_orders":
                    "Daily Orders",

                "warehouse":
                    "Warehouse",

                "distance_km":
                    "Distance (km)",

                "weighted_distance":
                    "Weighted Distance",

                "delivery_cost":
                    "Delivery Cost"
            }
        )
    )


    st.dataframe(

        assignment_df,

        use_container_width=True,

        hide_index=True
    )


    # ========================================================
    # WAREHOUSE UTILIZATION
    # ========================================================

    st.subheader(
        "🏢 Warehouse Utilization"
    )


    utilization = data[
        "warehouse_utilization"
    ]


    utilization_df = pd.DataFrame(
        utilization
    )


    utilization_df = (
        utilization_df.rename(

            columns={

                "warehouse_id":
                    "Warehouse",

                "daily_orders":
                    "Daily Orders",

                "capacity":
                    "Capacity",

                "utilization_percent":
                    "Utilization (%)"
            }
        )
    )


    st.dataframe(

        utilization_df,

        use_container_width=True,

        hide_index=True
    )


    # ========================================================
    # ORIGINAL VS OPTIMIZED
    # ========================================================

    st.header(
        "📊 Original vs Optimized"
    )


    original_distance = metrics[
        "original_weighted_distance"
    ]


    optimized_distance = metrics[
        "optimized_weighted_distance"
    ]


    original_cost = metrics[
        "original_delivery_cost"
    ]


    optimized_cost = metrics[
        "optimized_delivery_cost"
    ]


    distance_improvement = metrics[
        "distance_improvement_percent"
    ]


    cost_improvement = metrics[
        "cost_improvement_percent"
    ]


    comparison_df = pd.DataFrame(

        {

            "Metric": [

                "Weighted Delivery Distance",

                "Delivery Cost"
            ],


            "Original": [

                original_distance,

                original_cost
            ],


            "Optimized": [

                optimized_distance,

                optimized_cost
            ],


            "Improvement (%)": [

                distance_improvement,

                cost_improvement
            ]
        }
    )


    st.dataframe(

        comparison_df.style.format(

            {

                "Original":
                    "{:,.2f}",

                "Optimized":
                    "{:,.2f}",

                "Improvement (%)":
                    "{:,.2f}%"
            }
        ),

        use_container_width=True,

        hide_index=True
    )


    # ========================================================
    # IMPROVEMENT METRICS
    # ========================================================

    c1, c2 = (
        st.columns(2)
    )


    with c1:

        st.metric(

            "Distance Improvement",

            f"{distance_improvement:.2f}%"
        )


    with c2:

        st.metric(

            "Cost Improvement",

            f"{cost_improvement:.2f}%"
        )


    # ========================================================
    # DOWNLOAD
    # ========================================================

    st.subheader(
        "⬇️ Download Results"
    )


    result_download = pd.DataFrame(
        assignments
    )


    csv_data = (
        result_download.to_csv(
            index=False
        )
    )


    st.download_button(

        label="Download Assignment Results",

        data=csv_data,

        file_name=
            "warehouse_optimization_results.csv",

        mime="text/csv",

        use_container_width=True
    )


# ============================================================
# CSV FORMAT HELP
# ============================================================

with st.expander(
    "📋 Required CSV Format"
):

    st.code(
        """
neighborhood,latitude,longitude,daily_orders
Central,12.9716,77.5946,800
North,13.0358,77.5970,550
South,12.9116,77.6100,600
East,12.9850,77.6500,900
West,12.9507,77.5300,500
""",
        language="csv"
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Warehouse Location Optimization Platform | "
    "Streamlit + FastAPI + Python + Scikit-learn + Folium"
)
