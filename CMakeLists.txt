if(CONFIG_SOFLE_OLED_ART OR CONFIG_ZMK_BEHAVIOR_SOFLE_OLED_BG)
  zephyr_library()
  zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include) # ZMK headers
  zephyr_library_include_directories(include src/display src/display/generated)

  zephyr_library_sources_ifdef(CONFIG_ZMK_BEHAVIOR_SOFLE_OLED_BG src/behaviors/behavior_oled_bg.c)

  if(CONFIG_SOFLE_OLED_ART)
    zephyr_library_sources(src/display/fb.c src/display/status_screen.c)
    if(NOT CONFIG_ZMK_SPLIT OR CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
      zephyr_library_sources(src/display/left_screen.c src/display/generated/art_left.c)
    else()
      zephyr_library_sources(src/display/right_screen.c src/display/generated/art_frames.c)
    endif()
  endif()
endif()
