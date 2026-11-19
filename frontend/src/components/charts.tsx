"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function CountChart({ data }: { data: { name: string; count: number }[] }) {
  return (
    <div className="h-56 w-full min-w-0 overflow-hidden">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="#222225" />
          <XAxis dataKey="name" tick={{ fill: "#8b8b85", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fill: "#8b8b85", fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
          <Tooltip
            cursor={{ fill: "#17171a" }}
            contentStyle={{ background: "#121214", border: "1px solid #2c2c30", borderRadius: 2, color: "#ededea", fontSize: 12 }}
          />
          <Bar dataKey="count" fill="#ededea" radius={[1, 1, 0, 0]} maxBarSize={24} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
