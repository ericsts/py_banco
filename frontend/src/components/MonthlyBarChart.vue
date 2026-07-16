<script setup lang="ts">
import { computed, ref } from "vue";

const props = defineProps<{
  data: { mes: string; valor: number }[];
}>();

const hovered = ref<number | null>(null);

const W = 720;
const H = 220;
const PAD_LEFT = 8;
const PAD_RIGHT = 8;
const PAD_TOP = 12;
const PAD_BOTTOM = 28;
const GAP = 6;

const maxValor = computed(() => Math.max(1, ...props.data.map((d) => d.valor)));

const bars = computed(() => {
  const n = props.data.length || 1;
  const plotW = W - PAD_LEFT - PAD_RIGHT;
  const plotH = H - PAD_TOP - PAD_BOTTOM;
  const barW = Math.max(4, plotW / n - GAP);
  return props.data.map((d, i) => {
    const h = (d.valor / maxValor.value) * plotH;
    const x = PAD_LEFT + i * (plotW / n) + (plotW / n - barW) / 2;
    const y = PAD_TOP + plotH - h;
    return { ...d, x, y, w: barW, h, plotH };
  });
});

function fmt(v: number): string {
  return v.toLocaleString("pt-PT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
}
</script>

<template>
  <div class="relative">
    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full h-56">
      <line
        :x1="PAD_LEFT"
        :y1="H - PAD_BOTTOM"
        :x2="W - PAD_RIGHT"
        :y2="H - PAD_BOTTOM"
        stroke="#1e293b"
        stroke-width="1"
      />
      <g v-for="(b, i) in bars" :key="b.mes">
        <rect
          :x="b.x"
          :y="b.y"
          :width="b.w"
          :height="Math.max(b.h, 1)"
          rx="4"
          :fill="hovered === i ? '#5598e7' : '#3987e5'"
          class="cursor-pointer transition-colors"
          @mouseenter="hovered = i"
          @mouseleave="hovered = null"
        />
        <text
          :x="b.x + b.w / 2"
          :y="H - PAD_BOTTOM + 14"
          text-anchor="middle"
          font-size="9"
          fill="#64748b"
        >
          {{ b.mes.slice(2) }}
        </text>
      </g>
    </svg>

    <div
      v-if="hovered !== null"
      class="absolute pointer-events-none bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-xs text-slate-100 shadow-lg"
      :style="{
        left: `${(bars[hovered].x + bars[hovered].w / 2) / W * 100}%`,
        top: `${(bars[hovered].y / H) * 100}%`,
        transform: 'translate(-50%, -110%)',
      }"
    >
      <div class="font-medium">{{ bars[hovered].mes }}</div>
      <div>{{ fmt(bars[hovered].valor) }}</div>
    </div>
  </div>
</template>
