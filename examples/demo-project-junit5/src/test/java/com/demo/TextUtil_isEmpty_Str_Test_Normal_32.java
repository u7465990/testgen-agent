package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class TextUtil_isEmpty_Str_Test_Normal_32 {


    @Test
    public void testIsEmptyWithEmptyString() {
        String input = "";
        boolean expected = true;
        boolean actual = TextUtil.isEmpty(input);
        Assertions.assertEquals(expected, actual);
    }

    @Test
    public void testIsEmptyWithNonEmptyString() {
        String input = "test";
        boolean expected = false;
        boolean actual = TextUtil.isEmpty(input);
        Assertions.assertEquals(expected, actual);
    }

}
