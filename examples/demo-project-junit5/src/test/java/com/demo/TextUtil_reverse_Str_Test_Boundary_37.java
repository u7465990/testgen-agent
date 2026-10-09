package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class TextUtil_reverse_Str_Test_Boundary_37 {


    @Test
    public void testReverseWithNullInput() {
        String input = null;
        String result = TextUtil.reverse(input);
        Assertions.assertNull(result);
    }

}
