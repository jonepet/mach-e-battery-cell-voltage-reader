import { inject, provide, ref, type InjectionKey, type Ref } from 'vue';

export interface GroupHover {
  readonly group: Readonly<Ref<number | null>>;
  readonly set: (group: number | null) => void;
}

const key: InjectionKey<GroupHover> = Symbol('groupHover');

export function provideGroupHover(): GroupHover {
  const group = ref<number | null>(null);
  const hover: GroupHover = {
    group,
    set: (next) => {
      group.value = next;
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
