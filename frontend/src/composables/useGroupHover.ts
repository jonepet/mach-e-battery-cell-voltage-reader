import { inject, provide, ref, type InjectionKey, type Ref } from 'vue';

export interface GroupHover {
  readonly group: Readonly<Ref<number | null>>;
  readonly enter: (group: number, event: PointerEvent) => void;
  readonly leave: (event: PointerEvent) => void;
  readonly tap: (group: number, event: PointerEvent) => void;
}

const key: InjectionKey<GroupHover> = Symbol('groupHover');

/** A mouse highlights while it points at a group; a touch or pen tap selects a group until it is tapped again,
 * because touch screens report the pointer leaving as soon as the finger lifts. */
export function provideGroupHover(): GroupHover {
  const group = ref<number | null>(null);
  const isMouse = (event: PointerEvent): boolean => event.pointerType === 'mouse';
  const hover: GroupHover = {
    group,
    enter: (next, event) => {
      if (isMouse(event)) {
        group.value = next;
      }
    },
    leave: (event) => {
      if (isMouse(event)) {
        group.value = null;
      }
    },
    tap: (next, event) => {
      if (!isMouse(event)) {
        group.value = group.value === next ? null : next;
      }
    },
  };
  provide(key, hover);
  return hover;
}

export function useGroupHover(): GroupHover {
  const hover = inject(key);
  if (hover === undefined) {
    throw new Error('Group hover state is not provided');
  }
  return hover;
}
