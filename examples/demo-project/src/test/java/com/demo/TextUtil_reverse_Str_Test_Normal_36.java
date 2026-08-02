package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_reverse_Str_Test_Normal_36 {


    @Test
    public void reverse_typicalInput_returnsReversedString() {
        Assert.assertEquals("tset", TextUtil.reverse("test"));
        Assert.assertEquals("", TextUtil.reverse(""));
    }

}
