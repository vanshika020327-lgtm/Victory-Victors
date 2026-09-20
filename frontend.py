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
    help="Enter 0 for unlimited capacity."
)


max_radius = st.sidebar.number_input(
    "Maximum Service Radius (km)",
    min_value=0.0,
    value=0.0,
    step=1.0,
    help="Enter 0 for unlimited radius."
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


# ============================================================
# SAMPLE DATA
# ============================================================

def get_sample_data():

    return pd.DataFrame(
        {

            "neighborhood":
                [
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

            "latitude":
                [
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

            "longitude":
                [
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

            "daily_orders":
                [
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
# LOAD DATA
# ============================================================

if data_option == "Sample Data":

    df = get_sample_data()


elif data_option == "Upload CSV":

    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV",
        type=["csv"]
    )

    if uploaded_file is None:

        st.info(
            "Upload a CSV file to continue."
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
        get_sample_data(),
        num_rows="dynamic",
        use_container_width=True
    )


# ============================================================
# CHECK COLUMNS
# ============================================================

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

    st.error(
        "Missing columns: "
        + ", ".join(missing)
    )

    st.stop()


# ============================================================
# DATA PREVIEW
# ============================================================

st.header(
    "📊 Neighborhood Data"
)


c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "Neighborhoods",
        len(df)
    )


with c2:

    st.metric(
        "Total Daily Orders",
        f"{df['daily_orders'].sum():,.0f}"
    )


with c3:

    st.metric(
        "Average Orders",
        f"{df['daily_orders'].mean():,.0f}"
    )


with c4:

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
# OPTIMIZE BUTTON
# ============================================================

st.header(
    "🚀 Run Optimization"
)


run_optimization = st.button(
    "Optimize Warehouse Locations",
    type="primary",
    use_container_width=True
)


if run_optimization:

    # --------------------------------------------------------
    # Local validation
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


    # --------------------------------------------------------
    # Prepare API request
    # --------------------------------------------------------

    neighborhoods = []

    for _, row in df.iterrows():

        neighborhoods.append(
            {
                "neighborhood":
                    str(
                        row["neighborhood"]
                    ),

                "latitude":
                    float(
                        row["latitude"]
                    ),

                "longitude":
                    float(
                        row["longitude"]
                    ),

                "daily_orders":
                    float(
                        row["daily_orders"]
                    )
            }
        )


    request_data = {

        "neighborhoods":
            neighborhoods,

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
            "Connecting to optimization backend..."
        ):

            response = requests.post(
                f"{API_URL}/optimize",
                json=request_data,
                timeout=120
            )


    except requests.exceptions.ConnectionError:

        st.error(
            """
            ❌ Could not connect to middleware.

            Make sure you have started:

            python middleware.py
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
                    "Unknown API error."
                )
            )

        except Exception:

            error_message = (
                response.text
            )

        st.error(
            f"❌ Optimization failed: "
            f"{error_message}"
        )

        st.stop()


    try:

        data = response.json()

    except Exception:

        st.error(
            "The middleware returned invalid JSON."
        )

        st.stop()


    if not data.get(
        "success",
        False
    ):

        st.error(
            data.get(
                "message",
                "Optimization failed."
            )
        )

        st.stop()


    # ========================================================
    # RESULTS
    # ========================================================

    st.success(
        "✅ Optimization completed successfully!"
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


    m1, m2, m3, m4 = st.columns(4)


    with m1:

        st.metric(
            "Warehouses",
            metrics[
                "number_of_warehouses"
            ]
        )


    with m2:

        st.metric(
            "Weighted Distance",
            f"{metrics['optimized_weighted_distance']:,.2f}"
        )


    with m3:

        st.metric(
            "Average Distance",
            f"{metrics['optimized_average_distance']:.2f} km"
        )


    with m4:

        st.metric(
            "Daily Delivery Cost",
            f"{metrics['optimized_delivery_cost']:,.2f}"
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


    # --------------------------------------------------------
    # Neighborhoods and assignment lines
    # --------------------------------------------------------

    for item in assignments:

        warehouse_index = (
            item["warehouse"] - 1
        )

        color = colors[
            warehouse_index
            %
            len(colors)
        ]


        folium.CircleMarker(

            location=[
                item["latitude"],
                item["longitude"]
            ],

            radius=7,

            color=color,

            fill=True,

            fill_color=color,

            fill_opacity=0.8,

            popup=(
                f"<b>"
                f"{item['neighborhood']}"
                f"</b><br>"
                f"Orders: "
                f"{item['daily_orders']}<br>"
                f"Warehouse: "
                f"{item['warehouse']}<br>"
                f"Distance: "
                f"{item['distance_km']:.2f} km<br>"
                f"Cost: "
                f"{item['delivery_cost']:.2f}"
            )
        ).add_to(
            optimized_map
        )


        warehouse = warehouses[
            warehouse_index
        ]


        folium.PolyLine(

            locations=[
                [
                    item["latitude"],
                    item["longitude"]
                ],

                [
                    warehouse["latitude"],
                    warehouse["longitude"]
