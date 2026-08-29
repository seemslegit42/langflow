import type React from "react";
import { forwardRef } from "react";
import SvgSwarmsIcon from "./SwarmsIcon";

export const SwarmsIcon = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <SvgSwarmsIcon ref={ref} {...props} />;
});
