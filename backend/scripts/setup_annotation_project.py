"""Create the human wrinkle-mask review project once Label Studio is running."""

from backend.libs.labelstudio_client import get_label_studio_client

TITLE = "Aphrodize wrinkle mask review"
LABEL_CONFIG = """
<View>
  <Header value="Mark visible wrinkle pixels on the aligned face. Skip unclear images." />
  <Image name="image" value="$image" zoom="true" />
  <BrushLabels name="wrinkle" toName="image">
    <Label value="Wrinkle" background="#ff3030" />
  </BrushLabels>
</View>
"""


def main() -> None:
    # Run once to obtain the project ID used when the worker publishes review tasks.
    client = get_label_studio_client()
    if client is None:
        raise SystemExit("Set LABEL_STUDIO_API_KEY first")
    for project in client.projects.list(title=TITLE):
        # Reuse the existing review project when setup is run again.
        if project.title == TITLE:
            print(f"LABEL_STUDIO_PROJECT_ID={project.id}")
            return
    # Install the BrushLabels interface used to draw wrinkle pixels.
    project = client.projects.create(title=TITLE, label_config=LABEL_CONFIG)
    print(f"LABEL_STUDIO_PROJECT_ID={project.id}")


if __name__ == "__main__":
    main()
