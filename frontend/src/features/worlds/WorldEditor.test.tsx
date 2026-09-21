import { fireEvent, render, screen } from "@testing-library/react";
import { WorldEditor } from "./WorldEditor";

it("submits the generated world and preserves edited memory", () => {
  const onSubmit = vi.fn();
  render(
    <WorldEditor
      mode="create"
      world={null}
      busy={false}
      onCancel={vi.fn()}
      onSubmit={onSubmit}
      randomWorld={{
        title: "Harbor",
        theme: "A flooded city",
        style_pack: "noir-sketch",
        preset: "noir-mystery",
        maturity_level: "teen",
        memory: "The gates are locked.",
      }}
    />,
  );
  fireEvent.change(screen.getByLabelText("Memory and lore"), {
    target: { value: "The gates open only at dawn." },
  });
  fireEvent.click(screen.getByLabelText("Branching choices"));
  fireEvent.click(screen.getByRole("button", { name: "Create world" }));
  expect(onSubmit).toHaveBeenCalledWith(
    expect.objectContaining({
      title: "Harbor",
      theme: "A flooded city",
      style_pack: "noir-sketch",
      memory: "The gates open only at dawn.",
      enable_choices: true,
    }),
  );
});

it("does not submit a whitespace-only title", () => {
  render(
    <WorldEditor
      mode="create"
      world={null}
      randomWorld={null}
      busy={false}
      onCancel={vi.fn()}
      onSubmit={vi.fn()}
    />,
  );
  fireEvent.change(screen.getByLabelText("World title"), {
    target: { value: "   " },
  });
  fireEvent.change(screen.getByLabelText("Premise"), {
    target: { value: "A story" },
  });
  expect(screen.getByRole("button", { name: "Create world" })).toBeDisabled();
});

it("uses saved creation defaults without overwriting a form in progress", () => {
  const props = {
    mode: "create" as const,
    world: null,
    randomWorld: null,
    busy: false,
    onCancel: vi.fn(),
    onSubmit: vi.fn(),
  };
  const { rerender } = render(
    <WorldEditor
      {...props}
      settings={{
        default_style_pack: "noir-sketch",
        default_preset: "noir-mystery",
      }}
    />,
  );
  expect(screen.getByLabelText("Art style")).toHaveValue("noir-sketch");
  expect(screen.getByLabelText("Story tone")).toHaveValue("noir-mystery");
  fireEvent.change(screen.getByLabelText("World title"), {
    target: { value: "My story" },
  });
  rerender(
    <WorldEditor
      {...props}
      settings={{
        default_style_pack: "storybook-ink",
        default_preset: "cozy-adventure",
      }}
    />,
  );
  expect(screen.getByLabelText("World title")).toHaveValue("My story");
  expect(screen.getByLabelText("Art style")).toHaveValue("noir-sketch");
});
