package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class TextUtil_reverse_Str_Test_Normal_36 {


    @Test
    public void testReverseWithTypicalInputs() {
        assertEquals("tset", TextUtil.reverse("test"));
        assertEquals("olleh", TextUtil.reverse("hello"));
        assertEquals("", TextUtil.reverse(""));
    }

}
