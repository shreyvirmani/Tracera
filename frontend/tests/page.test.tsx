import { render, screen } from "@testing-library/react";
import Home from "../app/page";

describe("Home page", () => {
  it("renders Tracera title", () => {
    render(<Home />);
    expect(screen.getByText("Tracera")).toBeInTheDocument();
  });

  it("renders subtitle", () => {
    render(<Home />);
    expect(screen.getByText("Website Risk Assessment Platform")).toBeInTheDocument();
  });

  it("renders bootstrap status", () => {
    render(<Home />);
    expect(screen.getByText("Project bootstrap completed.")).toBeInTheDocument();
  });
});