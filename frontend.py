import streamlit as st
import pandas as pd
import folium

from streamlit_folium import st_folium

from backend import (
    optimize_warehouses,
    calculate_cost,
    calculate_original_cost
)


# ============================================================
# PAGE CONFIG
# ============================================================

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
    Find optimal warehouse locations, assign neighborhoods,
    and minimize demand-weighted delivery cost.
    """
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ Optimization Settings"
)

number_of_warehouses = st.sidebar.number_input(
    "Number of Warehouses",
    min_value=1,
    max_value=20,
    value=2,
    step=1
)

cost_per_km = st.sidebar.number_input(
    "Delivery Cost per Order-KM",
    min_value=0.0,
    value=1.0,
    step=0.1
)

warehouse_capacity = st.sidebar.number_input(
    "Warehouse Capacity (orders/day)",
    min_value=0.0,
    value=0.0,
    step=100.0,
    help="Set to 0 for unlimited capacity."
)

max_radius = st.sidebar.number_input(
    "Maximum Service Radius (km)",
    min_value=0.0,
    value=0.0,
    step=1.0,
    help="Set to 0 for unlimited radius."
)


# ============================================================
# DATA INPUT
# ============================================================

st.sidebar.header(
    "📥 Data Input"
)

data_option = st.sidebar.selectbox(
    "Choose data source",
    [
        "Sample Data",
        "Upload CSV",
        "Enter Manually"
    ]
)


# ============================================================
# SAMPLE DATA
# ============================================================

def sample_data():

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
# GET DATA
# ============================================================

if data_option == "Sample Data":

    df = sample_data()


elif data_option == "Upload CSV":

    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV",
        type=["csv"]
    )

    if uploaded_file is None:

        st.info(
            "Please upload a CSV file."
        )

        st.stop()

    try:

        df = pd.read_csv(
            uploaded_file
        )

    except Exception as error:

        st.error(
            f"Could not read file: {error}"
        )

        st.stop()


else:

    df = st.data_editor(
        sample_data(),
        num_rows="dynamic",
        use_container_width=True
    )


# ============================================================
# VALIDATE BASIC COLUMNS
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
        "Missing columns: "
        + ", ".join(missing_columns)
    )

    st.stop()


# ============================================================
# DATA PREVIEW
# ============================================================

st.header(
    "📊 Neighborhood Data"
)

col1, col2, col3, col4 = st.columns(4)

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
    "🗺️ Neighborhood Map"
)


center_lat = df[
    "latitude"
].mean()

center_lon = df[
    "longitude"
].mean()


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

        popup=(
            f"<b>{row['neighborhood']}</b><br>"
            f"Orders: "
            f"{row['daily_orders']}"
        ),

        color="blue",

        fill=True,

        fill_color="blue",

        fill_opacity=0.7
    ).add_to(initial_map)


st_folium(
    initial_map,
    width=None,
    height=500
)


# ============================================================
# OPTIMIZATION BUTTON
# ============================================================

st.header(
    "🚀 Warehouse Optimization"
)

run = st.button(
    "Optimize Warehouse Locations",
    type="primary",
    use_container_width=True
)


if run:

    if number_of_warehouses > len(df):

        st.error(
            "Number of warehouses cannot exceed "
            "number of neighborhoods."
        )

        st.stop()

    try:

        with st.spinner(
            "Running optimization..."
        ):

            (
                result,
                warehouse_locations,
                distance_matrix
            ) = optimize_warehouses(

                df,

                int(
                    number_of_warehouses
                ),

                warehouse_capacity
                if warehouse_capacity > 0
                else None,

                max_radius
                if max_radius > 0
                else None
            )


            (
                result,
                total_distance,
                total_cost,
                average_distance
            ) = calculate_cost(

                result,

                cost_per_km
            )


            (
                original_lat,
                original_lon,
                original_distance,
                original_cost
            ) = calculate_original_cost(

                df,

                cost_per_km
            )


        # ====================================================
        # RESULTS
        # ====================================================

        st.success(
            "Optimization completed successfully!"
        )


        # ====================================================
        # METRICS
        # ====================================================

        st.subheader(
            "📈 Optimization Results"
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Warehouses",
                number_of_warehouses
            )

        with c2:

            st.metric(
                "Weighted Distance",
                f"{total_distance:,.2f} km"
            )

        with c3:

            st.metric(
                "Average Distance",
                f"{average_distance:.2f} km"
            )

        with c4:

            st.metric(
                "Daily Delivery Cost",
                f"{total_cost:,.2f}"
            )


        # ====================================================
        # WAREHOUSE LOCATIONS
        # ====================================================

        st.subheader(
            "🏭 Optimized Warehouse Locations"
        )

        warehouse_data = []

        for i, location in enumerate(
            warehouse_locations
        ):

            warehouse_data.append(
                {
                    "Warehouse":
                        f"Warehouse {i + 1}",

                    "Latitude":
                        round(
                            location[0],
                            6
                        ),

                    "Longitude":
                        round(
                            location[1],
                            6
                        )
                }
            )

        warehouse_df = pd.DataFrame(
            warehouse_data
        )

        st.dataframe(
            warehouse_df,
            use_container_width=True,
            hide_index=True
        )


        # ====================================================
        # OPTIMIZED MAP
        # ====================================================

        st.subheader(
            "🗺️ Optimized Warehouse Map"
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


        # ----------------------------------------------------
        # Neighborhoods
        # ----------------------------------------------------

        for index, row in result.iterrows():

            warehouse_id = (
                int(
                    row["warehouse"]
                ) - 1
            )

            color = colors[
                warehouse_id
                % len(colors)
            ]

            folium.CircleMarker(

                location=[
                    row["latitude"],
                    row["longitude"]
                ],

                radius=7,

                color=color,

                fill=True,

                fill_color=color,

                fill_opacity=0.8,

                popup=(
                    f"<b>"
                    f"{row['neighborhood']}"
                    f"</b><br>"
                    f"Daily Orders: "
                    f"{row['daily_orders']}<br>"
                    f"Warehouse: "
                    f"{row['warehouse']}<br>"
                    f"Distance: "
                    f"{row['distance_km']:.2f} km"
                )
            ).add_to(
                optimized_map
            )


            # ------------------------------------------------
            # Assignment line
            # ------------------------------------------------

            warehouse = (
                warehouse_locations[
                    warehouse_id
                ]
            )

            folium.PolyLine(

                locations=[
                    [
                        row["latitude"],
                        row["longitude"]
                    ],

                    [
                        warehouse[0],
                        warehouse[1]
                    ]
                ],

                color=color,

                weight=1,

                opacity=0.5

            ).add_to(
                optimized_map
            )


        # ----------------------------------------------------
        # Warehouses
        # ----------------------------------------------------

        for i, location in enumerate(
            warehouse_locations
        ):

            color = colors[
                i % len(colors)
            ]

            folium.Marker(

                location=[
                    location[0],
                    location[1]
                ],

                popup=(
                    f"<b>"
                    f"Warehouse {i + 1}"
                    f"</b><br>"
                    f"Latitude: "
                    f"{location[0]:.6f}<br>"
                    f"Longitude: "
                    f"{location[1]:.6f}"
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


        # ====================================================
        # ASSIGNMENTS
        # ====================================================

        st.subheader(
            "📦 Neighborhood Assignments"
        )

        display_result = result[
            [
                "neighborhood",
                "latitude",
                "longitude",
                "daily_orders",
                "warehouse",
                "distance_km",
                "weighted_distance",
                "delivery_cost"
            ]
        ].copy()


        display_result.columns = [
            "Neighborhood",
            "Latitude",
            "Longitude",
            "Daily Orders",
            "Assigned Warehouse",
            "Distance (km)",
            "Weighted Distance",
            "Delivery Cost"
        ]


        st.dataframe(
            display_result,
            use_container_width=True,
            hide_index=True
        )


        # ====================================================
        # COMPARISON
        # ====================================================

        st.header(
            "📊 Original vs Optimized"
        )


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


        comparison = pd.DataFrame(
            {
                "Metric": [
                    "Weighted Distance",
                    "Delivery Cost"
                ],

                "Original": [
                    original_distance,
                    original_cost
                ],

                "Optimized": [
                    total_distance,
                    total_cost
                ],

                "Improvement (%)": [
                    distance_improvement,
                    cost_improvement
                ]
            }
        )


        st.dataframe(
            comparison.style.format(
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


        c1, c2 = st.columns(2)

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


        # ====================================================
        # DOWNLOAD
        # ====================================================

        st.subheader(
            "⬇️ Download Results"
        )


        csv = result.to_csv(
            index=False
        )


        st.download_button(

            label="Download Results CSV",

            data=csv,

            file_name=
                "warehouse_optimization_results.csv",

            mime="text/csv",

            use_container_width=True
        )


    except Exception as error:

        st.error(
            f"Optimization error: {error}"
        )


# ============================================================
# CSV FORMAT
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
    "Python + Streamlit + Scikit-learn + Folium"
)

