# create a tumbnail for the video
# settingsbackground = settings.config["settings"]["background"]

# if settingsbackground["background_thumbnail"]:
#     if not exists(f"./results/{subreddit}/thumbnails"):
#         print_substep(
#             "The results/thumbnails folder didn't exist so I made it")
#         os.makedirs(f"./results/{subreddit}/thumbnails")
#     # get the first file with the .png extension from assets/backgrounds and use it as a background for the thumbnail
#     first_image = next(
#         (
#             file
#             for file in os.listdir("assets/backgrounds")
#             if file.endswith(".png")
#         ),
#         None,
#     )
#     if first_image is None:
#         print_substep("No png files found in assets/backgrounds", "red")

# if settingsbackground["background_thumbnail"] and first_image:
#     font_family = settingsbackground["background_thumbnail_font_family"]
#     font_size = settingsbackground["background_thumbnail_font_size"]
#     font_color = settingsbackground["background_thumbnail_font_color"]
#     thumbnail = Image.open(f"assets/backgrounds/{first_image}")
#     width, height = thumbnail.size
#     thumbnailSave = create_thumbnail(thumbnail, font_family, font_size, font_color, width, height, title_thumb)
#     thumbnailSave.save(f"./assets/temp/{reddit_id}/thumbnail.png")
#     print_substep(f"Thumbnail - Building Thumbnail in assets/temp/{reddit_id}/thumbnail.png")

# create a tumbnail for the video
# settingsbackground = settings.config["settings"]["background"]

# if settingsbackground["background_thumbnail"]:
#     if not exists(f"./results/{subreddit}/thumbnails"):
#         print_substep(
#             "The results/thumbnails folder didn't exist so I made it")
#         os.makedirs(f"./results/{subreddit}/thumbnails")
#     # get the first file with the .png extension from assets/backgrounds and use it as a background for the thumbnail
#     first_image = next(
#         (
#             file
#             for file in os.listdir("assets/backgrounds")
#             if file.endswith(".png")
#         ),
#         None,
#     )
#     if first_image is None:
#         print_substep("No png files found in assets/backgrounds", "red")

# if settingsbackground["background_thumbnail"] and first_image:
#     font_family = settingsbackground["background_thumbnail_font_family"]
#     font_size = settingsbackground["background_thumbnail_font_size"]
#     font_color = settingsbackground["background_thumbnail_font_color"]
#     thumbnail = Image.open(f"assets/backgrounds/{first_image}")
#     width, height = thumbnail.size
# thumbnailSave = create_thumbnail(thumbnail, font_family, font_size, font_color, width, height, title_thumb)
# thumbnailSave.save(f"./assets/temp/{reddit_id}/thumbnail.png")
# print_substep(f"Thumbnail - Building Thumbnail in assets/temp/{reddit_id}/thumbnail.png")

# get the thumbnail image from assets/temp/id/thumbnail.png and save it in results/subreddit/thumbnails
# if settingsbackground["background_thumbnail"] and exists(f"assets/temp/{reddit_id}/thumbnail.png"):
# shutil.move(f"assets/temp/{reddit_id}/thumbnail.png", f"./results/{subreddit}/thumbnails/{filename}.png")
