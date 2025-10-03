// Highway Design Standards - Global Object
// Based on AASHTO standards for geometric design
window.designStandards = {
  "standard": "Highway Design Standards",
  "version": "1.0",
  "description": "Generic highway geometric design criteria based on AASHTO standards",
  "design_criteria": {
    "horizontal_curve": {
      "description": "Minimum radius requirements for horizontal curves based on design speed and maximum superelevation",
      "minimum_radius_by_speed": {
        "15_mph": {
          "emax_4_percent_ft": 69,
          "emax_6_percent_ft": 66,
          "emax_8_percent_ft": 63,
          "emax_10_percent_ft": 60
        },
        "20_mph": {
          "emax_4_percent_ft": 118,
          "emax_6_percent_ft": 112,
          "emax_8_percent_ft": 107,
          "emax_10_percent_ft": 103
        },
        "25_mph": {
          "emax_4_percent_ft": 154,
          "emax_6_percent_ft": 144,
          "emax_8_percent_ft": 136,
          "emax_10_percent_ft": 129
        },
        "30_mph": {
          "emax_4_percent_ft": 250,
          "emax_6_percent_ft": 231,
          "emax_8_percent_ft": 217,
          "emax_10_percent_ft": 205
        },
        "35_mph": {
          "emax_4_percent_ft": 371,
          "emax_6_percent_ft": 340,
          "emax_8_percent_ft": 316,
          "emax_10_percent_ft": 297
        },
        "40_mph": {
          "emax_4_percent_ft": 533,
          "emax_6_percent_ft": 485,
          "emax_8_percent_ft": 447,
          "emax_10_percent_ft": 417
        },
        "45_mph": {
          "emax_4_percent_ft": 711,
          "emax_6_percent_ft": 643,
          "emax_8_percent_ft": 589,
          "emax_10_percent_ft": 546
        },
        "50_mph": {
          "emax_4_percent_ft": 926,
          "emax_6_percent_ft": 833,
          "emax_8_percent_ft": 759,
          "emax_10_percent_ft": 699
        },
        "55_mph": {
          "emax_4_percent_ft": 1175,
          "emax_6_percent_ft": 1050,
          "emax_8_percent_ft": 952,
          "emax_10_percent_ft": 874
        },
        "60_mph": {
          "emax_4_percent_ft": 1460,
          "emax_6_percent_ft": 1296,
          "emax_8_percent_ft": 1168,
          "emax_10_percent_ft": 1067
        },
        "65_mph": {
          "emax_4_percent_ft": 1780,
          "emax_6_percent_ft": 1570,
          "emax_8_percent_ft": 1408,
          "emax_10_percent_ft": 1281
        },
        "70_mph": {
          "emax_4_percent_ft": 2137,
          "emax_6_percent_ft": 1873,
          "emax_8_percent_ft": 1670,
          "emax_10_percent_ft": 1514
        },
        "75_mph": {
          "emax_4_percent_ft": 2528,
          "emax_6_percent_ft": 2204,
          "emax_8_percent_ft": 1954,
          "emax_10_percent_ft": 1765
        },
        "80_mph": {
          "emax_4_percent_ft": 2955,
          "emax_6_percent_ft": 2564,
          "emax_8_percent_ft": 2260,
          "emax_10_percent_ft": 2034
        }
      }
    },
    "superelevation": {
      "description": "Maximum superelevation rates for different road types",
      "maximum_rates": {
        "rural_highways": {
          "emax_percent": 8,
          "description": "Rural highways, high-speed facilities"
        },
        "urban_suburban": {
          "emax_percent": 6,
          "description": "Urban and suburban areas with frequent intersections"
        },
        "low_speed_urban": {
          "emax_percent": 4,
          "description": "Low-speed urban streets, heavily developed areas"
        },
        "special_conditions": {
          "ice_snow_frequent": {
            "emax_percent": 6,
            "description": "Areas with frequent ice and snow"
          },
          "urban_core": {
            "emax_percent": 4,
            "description": "Urban core areas with high pedestrian activity"
          }
        }
      },
      "transition": {
        "runoff_length": "Superelevation runoff length varies with design speed and number of lanes rotated",
        "tangent_runout": "Remove adverse crown before introducing superelevation"
      }
    },
    "grade": {
      "description": "Maximum grades based on design speed and terrain type",
      "maximum_by_speed_and_terrain": {
        "20_mph": {
          "level_percent": 11,
          "rolling_percent": 14,
          "mountainous_percent": 16
        },
        "25_mph": {
          "level_percent": 9,
          "rolling_percent": 12,
          "mountainous_percent": 14
        },
        "30_mph": {
          "level_percent": 9,
          "rolling_percent": 11,
          "mountainous_percent": 12
        },
        "35_mph": {
          "level_percent": 9,
          "rolling_percent": 10,
          "mountainous_percent": 11
        },
        "40_mph": {
          "level_percent": 8,
          "rolling_percent": 10,
          "mountainous_percent": 11
        },
        "45_mph": {
          "level_percent": 8,
          "rolling_percent": 9,
          "mountainous_percent": 10
        },
        "50_mph": {
          "level_percent": 7,
          "rolling_percent": 8,
          "mountainous_percent": 9
        },
        "55_mph": {
          "level_percent": 6,
          "rolling_percent": 7,
          "mountainous_percent": 8
        },
        "60_mph": {
          "level_percent": 5,
          "rolling_percent": 6,
          "mountainous_percent": 7
        },
        "65_mph": {
          "level_percent": 4,
          "rolling_percent": 5,
          "mountainous_percent": 6
        },
        "70_mph": {
          "level_percent": 4,
          "rolling_percent": 5,
          "mountainous_percent": 6
        },
        "75_mph": {
          "level_percent": 3,
          "rolling_percent": 4,
          "mountainous_percent": 5
        },
        "80_mph": {
          "level_percent": 3,
          "rolling_percent": 4,
          "mountainous_percent": 5
        }
      },
      "terrain_definitions": {
        "level": "Any combination of grades and horizontal/vertical alignment permitting heavy vehicles to maintain same speed as passenger cars",
        "rolling": "Natural slopes consistently rise above and fall below the roadway grade causing heavy vehicles to reduce speed below passenger cars but not to crawl speeds",
        "mountainous": "Steep slopes causing heavy vehicles to operate at crawl speeds for significant distances or at frequent intervals"
      },
      "critical_length": {
        "description": "Maximum length of grade on which a loaded truck can operate without unreasonable speed reduction",
        "criteria": "Grades longer than critical length may require climbing lanes or other design treatments"
      }
    },
    "vertical_curve": {
      "description": "Minimum lengths for vertical curves based on design speed and algebraic difference in grades",
      "crest_curves": {
        "design_control": "Stopping sight distance",
        "length_formula": "L = KA, where A is algebraic difference in grades (percent) and K is rate of vertical curvature"
      },
      "sag_curves": {
        "design_control": "Headlight sight distance, passenger comfort, drainage, and general appearance",
        "length_formula": "L = KA, where A is algebraic difference in grades (percent) and K is rate of vertical curvature"
      }
    },
    "stopping_sight_distance": {
      "description": "Minimum sight distance to allow driver to stop before reaching stationary object",
      "assumptions": {
        "perception_reaction_time_seconds": 2.5,
        "deceleration_rate_ft_per_sec2": 11.2,
        "brake_reaction_time": "Includes perception and decision time"
      },
      "by_design_speed": {
        "15_mph": {
          "min_ft": 80
        },
        "20_mph": {
          "min_ft": 115
        },
        "25_mph": {
          "min_ft": 155
        },
        "30_mph": {
          "min_ft": 200
        },
        "35_mph": {
          "min_ft": 250
        },
        "40_mph": {
          "min_ft": 305
        },
        "45_mph": {
          "min_ft": 360
        },
        "50_mph": {
          "min_ft": 425
        },
        "55_mph": {
          "min_ft": 495
        },
        "60_mph": {
          "min_ft": 570
        },
        "65_mph": {
          "min_ft": 645
        },
        "70_mph": {
          "min_ft": 730
        },
        "75_mph": {
          "min_ft": 820
        },
        "80_mph": {
          "min_ft": 910
        }
      }
    },
    "cross_slope": {
      "description": "Transverse slope on tangent sections for drainage",
      "normal_crown": {
        "min_percent": 1.5,
        "max_percent": 2.5,
        "typical_percent": 2.0
      },
      "high_type_pavement": {
        "typical_percent": 2.0,
        "description": "Portland cement concrete, high-type bituminous"
      },
      "intermediate_pavement": {
        "typical_percent": 2.5,
        "description": "Intermediate bituminous surfaces"
      },
      "low_type_pavement": {
        "typical_percent": 3.0,
        "description": "Low-type bituminous, surface treatment"
      }
    }
  },
  "validation_notes": {
    "general": "These standards are based on AASHTO 'A Policy on Geometric Design of Highways and Streets' (Green Book)",
    "flexibility": "Design values may be adjusted based on project-specific conditions, context, and constraints with proper engineering analysis",
    "speed_selection": "Design speed should be selected based on roadway classification, terrain, adjacent development, and functional requirements"
  }
};



