import { NextResponse } from "next/server";
import samples from "@/data/samples.json";

export function GET() {
  return NextResponse.json(samples);
}
